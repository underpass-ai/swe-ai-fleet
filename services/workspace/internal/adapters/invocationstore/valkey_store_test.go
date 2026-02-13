package invocationstore

import (
	"context"
	"encoding/json"
	"errors"
	"testing"
	"time"

	redis "github.com/redis/go-redis/v9"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
)

type fakeValkeyClient struct {
	data    map[string]string
	pingErr error
	setErr  error
	getErr  error
}

func (f *fakeValkeyClient) Ping(_ context.Context) *redis.StatusCmd {
	return redis.NewStatusResult("PONG", f.pingErr)
}

func (f *fakeValkeyClient) Set(_ context.Context, key string, value interface{}, _ time.Duration) *redis.StatusCmd {
	if f.setErr != nil {
		return redis.NewStatusResult("", f.setErr)
	}
	if f.data == nil {
		f.data = map[string]string{}
	}
	switch typed := value.(type) {
	case []byte:
		f.data[key] = string(typed)
	case string:
		f.data[key] = typed
	default:
		payload, _ := json.Marshal(typed)
		f.data[key] = string(payload)
	}
	return redis.NewStatusResult("OK", nil)
}

func (f *fakeValkeyClient) Get(_ context.Context, key string) *redis.StringCmd {
	if f.getErr != nil {
		return redis.NewStringResult("", f.getErr)
	}
	value, ok := f.data[key]
	if !ok {
		return redis.NewStringResult("", redis.Nil)
	}
	return redis.NewStringResult(value, nil)
}

func TestValkeyStore_SaveAndGet(t *testing.T) {
	client := &fakeValkeyClient{data: map[string]string{}}
	store := NewValkeyStore(client, "workspace:test", time.Hour)

	invocation := domain.Invocation{
		ID:        "inv-1",
		SessionID: "session-1",
		ToolName:  "fs.read",
		Status:    domain.InvocationStatusSucceeded,
		StartedAt: time.Now().UTC(),
		Output:    map[string]any{"content": "ok"},
	}

	if err := store.Save(context.Background(), invocation); err != nil {
		t.Fatalf("save failed: %v", err)
	}

	stored, found, err := store.Get(context.Background(), invocation.ID)
	if err != nil {
		t.Fatalf("get failed: %v", err)
	}
	if !found {
		t.Fatalf("expected invocation to be found")
	}
	if stored.ID != invocation.ID {
		t.Fatalf("unexpected invocation id: %s", stored.ID)
	}
}

func TestValkeyStore_GetMissing(t *testing.T) {
	store := NewValkeyStore(&fakeValkeyClient{data: map[string]string{}}, "", 0)
	_, found, err := store.Get(context.Background(), "missing")
	if err != nil {
		t.Fatalf("unexpected get error: %v", err)
	}
	if found {
		t.Fatalf("expected missing invocation")
	}
}

func TestValkeyStore_SaveErrors(t *testing.T) {
	store := NewValkeyStore(&fakeValkeyClient{setErr: errors.New("set failed")}, "workspace:test", 0)
	err := store.Save(context.Background(), domain.Invocation{ID: "inv-1"})
	if err == nil {
		t.Fatalf("expected save error")
	}
}

func TestValkeyStore_GetErrors(t *testing.T) {
	store := NewValkeyStore(&fakeValkeyClient{getErr: errors.New("get failed")}, "workspace:test", 0)
	_, _, err := store.Get(context.Background(), "inv-1")
	if err == nil {
		t.Fatalf("expected get error")
	}
}

func TestValkeyStore_GetInvalidJSON(t *testing.T) {
	store := NewValkeyStore(&fakeValkeyClient{
		data: map[string]string{"workspace:test:inv-bad": "{not-json"},
	}, "workspace:test", 0)

	_, _, err := store.Get(context.Background(), "inv-bad")
	if err == nil {
		t.Fatalf("expected unmarshal error")
	}
}

func TestValkeyStore_DefaultPrefix(t *testing.T) {
	store := NewValkeyStore(&fakeValkeyClient{}, " ", 0)
	if store.keyPrefix != "workspace:invocation" {
		t.Fatalf("expected default prefix, got %s", store.keyPrefix)
	}
}

func TestNewValkeyStoreFromAddress_InvalidAddress(t *testing.T) {
	_, err := NewValkeyStoreFromAddress(
		context.Background(),
		"127.0.0.1:0",
		"",
		0,
		"",
		time.Second,
	)
	if err == nil {
		t.Fatalf("expected connection error")
	}
}

func TestValkeyStore_Key(t *testing.T) {
	store := NewValkeyStore(&fakeValkeyClient{}, "workspace:test", 0)
	if key := store.key("inv-1"); key != "workspace:test:inv-1" {
		t.Fatalf("unexpected key: %s", key)
	}
}
