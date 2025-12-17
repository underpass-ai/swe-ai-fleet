package store

import (
	"context"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
	"github.com/redis/go-redis/v9"
)

func TestRedisStore_PersistsAcrossRestartAndExpiresWithTTL(t *testing.T) {
	mr, err := miniredis.Run()
	if err != nil {
		t.Fatalf("miniredis.Run: %v", err)
	}
	defer mr.Close()

	ctx := context.Background()

	client1 := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	store1, err := NewRedisStore(client1, "test")
	if err != nil {
		t.Fatalf("NewRedisStore: %v", err)
	}

	now := time.Now().UTC()
	rec := DeliberationRecord{
		DeliberationID: "d-1",
		TaskID:         "task-1",
		Status:         DeliberationStatusRunning,
		CreatedAtUTC:   now,
		UpdatedAtUTC:   now,
		Metadata:       map[string]string{"story_id": "story-1"},
	}

	if err := store1.Upsert(ctx, rec, 2*time.Second); err != nil {
		t.Fatalf("Upsert: %v", err)
	}

	// Simulate process restart: new client/store.
	client2 := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	store2, err := NewRedisStore(client2, "test")
	if err != nil {
		t.Fatalf("NewRedisStore (2): %v", err)
	}

	got, ok, err := store2.Get(ctx, "d-1")
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if !ok {
		t.Fatalf("expected record to exist")
	}
	if got.DeliberationID != "d-1" || got.TaskID != "task-1" {
		t.Fatalf("unexpected record: %+v", got)
	}

	// Advance time beyond TTL and ensure record is gone.
	mr.FastForward(3 * time.Second)

	_, ok, err = store2.Get(ctx, "d-1")
	if err != nil {
		t.Fatalf("Get after ttl: %v", err)
	}
	if ok {
		t.Fatalf("expected record to expire")
	}
}

func TestRedisStore_ListActiveCleansUpStaleEntries(t *testing.T) {
	mr, err := miniredis.Run()
	if err != nil {
		t.Fatalf("miniredis.Run: %v", err)
	}
	defer mr.Close()

	ctx := context.Background()
	client := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	st, err := NewRedisStore(client, "test")
	if err != nil {
		t.Fatalf("NewRedisStore: %v", err)
	}

	now := time.Now().UTC()
	if err := st.Upsert(ctx, DeliberationRecord{
		DeliberationID: "d-1",
		TaskID:         "task-1",
		Status:         DeliberationStatusRunning,
		CreatedAtUTC:   now,
		UpdatedAtUTC:   now,
	}, 1*time.Second); err != nil {
		t.Fatalf("Upsert: %v", err)
	}

	mr.FastForward(2 * time.Second)

	active, err := st.ListActive(ctx, 10)
	if err != nil {
		t.Fatalf("ListActive: %v", err)
	}
	if len(active) != 0 {
		t.Fatalf("expected 0 active, got %d", len(active))
	}
}
