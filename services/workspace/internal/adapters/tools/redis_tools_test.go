package tools

import (
	"context"
	"encoding/json"
	"errors"
	"testing"
	"time"

	redis "github.com/redis/go-redis/v9"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
)

type fakeRedisClient struct {
	get    func(endpoint, key string) (string, error)
	mget   func(endpoint string, keys []string) ([]any, error)
	scan   func(endpoint string, cursor uint64, match string, count int64) ([]string, uint64, error)
	ttl    func(endpoint, key string) (time.Duration, error)
	exists func(endpoint string, keys []string) (int64, error)
}

func (f *fakeRedisClient) Get(_ context.Context, endpoint, key string) (string, error) {
	if f.get != nil {
		return f.get(endpoint, key)
	}
	return "", redis.Nil
}

func (f *fakeRedisClient) MGet(_ context.Context, endpoint string, keys []string) ([]any, error) {
	if f.mget != nil {
		return f.mget(endpoint, keys)
	}
	return []any{}, nil
}

func (f *fakeRedisClient) Scan(_ context.Context, endpoint string, cursor uint64, match string, count int64) ([]string, uint64, error) {
	if f.scan != nil {
		return f.scan(endpoint, cursor, match, count)
	}
	return []string{}, 0, nil
}

func (f *fakeRedisClient) TTL(_ context.Context, endpoint, key string) (time.Duration, error) {
	if f.ttl != nil {
		return f.ttl(endpoint, key)
	}
	return -2 * time.Second, nil
}

func (f *fakeRedisClient) Exists(_ context.Context, endpoint string, keys []string) (int64, error) {
	if f.exists != nil {
		return f.exists(endpoint, keys)
	}
	return 0, nil
}

func TestRedisGetHandler_Success(t *testing.T) {
	handler := NewRedisGetHandler(&fakeRedisClient{
		get: func(endpoint, key string) (string, error) {
			if endpoint == "" || key != "sandbox:todo:1" {
				t.Fatalf("unexpected get request: endpoint=%q key=%q", endpoint, key)
			}
			return "hello", nil
		},
	})
	session := domain.Session{
		Metadata: map[string]string{
			"connection_profile_endpoints_json": `{"dev.redis":"valkey:6379"}`,
		},
	}

	result, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"profile_id":"dev.redis","key":"sandbox:todo:1"}`))
	if err != nil {
		t.Fatalf("unexpected redis.get error: %#v", err)
	}
	output, ok := result.Output.(map[string]any)
	if !ok {
		t.Fatalf("expected map output, got %#v", result.Output)
	}
	if output["found"] != true {
		t.Fatalf("expected found=true, got %#v", output["found"])
	}
}

func TestRedisGetHandler_DeniesKeyOutsideProfileScopes(t *testing.T) {
	handler := NewRedisGetHandler(&fakeRedisClient{})
	session := domain.Session{
		Metadata: map[string]string{
			"connection_profile_endpoints_json": `{"dev.redis":"valkey:6379"}`,
		},
	}

	_, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"profile_id":"dev.redis","key":"prod:secret"}`))
	if err == nil {
		t.Fatal("expected key policy denial")
	}
	if err.Code != app.ErrorCodePolicyDenied {
		t.Fatalf("unexpected error code: %s", err.Code)
	}
}

func TestRedisScanHandler_Success(t *testing.T) {
	handler := NewRedisScanHandler(&fakeRedisClient{
		scan: func(endpoint string, cursor uint64, match string, count int64) ([]string, uint64, error) {
			if match != "sandbox:*" {
				t.Fatalf("unexpected scan match: %s", match)
			}
			return []string{"sandbox:todo:1", "sandbox:todo:2"}, 0, nil
		},
	})
	session := domain.Session{
		Metadata: map[string]string{
			"connection_profile_endpoints_json": `{"dev.redis":"valkey:6379"}`,
		},
	}

	result, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"profile_id":"dev.redis","prefix":"sandbox:"}`))
	if err != nil {
		t.Fatalf("unexpected redis.scan error: %#v", err)
	}
	output, ok := result.Output.(map[string]any)
	if !ok {
		t.Fatalf("expected map output, got %#v", result.Output)
	}
	if output["count"] != 2 {
		t.Fatalf("unexpected scan count: %#v", output["count"])
	}
}

func TestRedisExistsHandler_MapsExecutionErrors(t *testing.T) {
	handler := NewRedisExistsHandler(&fakeRedisClient{
		exists: func(endpoint string, keys []string) (int64, error) {
			return 0, errors.New("dial failed")
		},
	})
	session := domain.Session{
		Metadata: map[string]string{
			"connection_profile_endpoints_json": `{"dev.redis":"valkey:6379"}`,
		},
	}

	_, err := handler.Invoke(context.Background(), session, json.RawMessage(`{"profile_id":"dev.redis","keys":["sandbox:todo:1"]}`))
	if err == nil {
		t.Fatal("expected execution error")
	}
	if err.Code != app.ErrorCodeExecutionFailed {
		t.Fatalf("unexpected error code: %s", err.Code)
	}
}
