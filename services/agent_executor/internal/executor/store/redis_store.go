package store

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
)

type RedisStore struct {
	client *redis.Client
	prefix string
}

func NewRedisStore(client *redis.Client, prefix string) (*RedisStore, error) {
	if client == nil {
		return nil, fmt.Errorf("redis client cannot be nil")
	}
	if prefix == "" {
		prefix = "agent-executor"
	}
	return &RedisStore{client: client, prefix: prefix}, nil
}

func (s *RedisStore) Upsert(ctx context.Context, record DeliberationRecord, ttl time.Duration) error {
	if record.DeliberationID == "" {
		return fmt.Errorf("deliberation_id cannot be empty")
	}
	if record.TaskID == "" {
		return fmt.Errorf("task_id cannot be empty")
	}
	if ttl <= 0 {
		return fmt.Errorf("ttl must be > 0")
	}

	payload, err := json.Marshal(record)
	if err != nil {
		return fmt.Errorf("marshal record: %w", err)
	}

	key := s.keyRecord(record.DeliberationID)
	activeKey := s.keyActiveIndex()

	pipe := s.client.Pipeline()
	pipe.Set(ctx, key, payload, ttl)
	pipe.SAdd(ctx, activeKey, record.DeliberationID)
	_, err = pipe.Exec(ctx)
	if err != nil {
		return fmt.Errorf("redis exec: %w", err)
	}
	return nil
}

func (s *RedisStore) Get(ctx context.Context, deliberationID string) (DeliberationRecord, bool, error) {
	if deliberationID == "" {
		return DeliberationRecord{}, false, fmt.Errorf("deliberation_id cannot be empty")
	}

	key := s.keyRecord(deliberationID)
	value, err := s.client.Get(ctx, key).Result()
	if err != nil {
		if err == redis.Nil {
			return DeliberationRecord{}, false, nil
		}
		return DeliberationRecord{}, false, fmt.Errorf("redis get: %w", err)
	}

	var rec DeliberationRecord
	if err := json.Unmarshal([]byte(value), &rec); err != nil {
		return DeliberationRecord{}, false, fmt.Errorf("unmarshal record: %w", err)
	}
	return rec, true, nil
}

func (s *RedisStore) Touch(ctx context.Context, deliberationID string, ttl time.Duration, updatedAtUTC time.Time) error {
	if deliberationID == "" {
		return fmt.Errorf("deliberation_id cannot be empty")
	}
	if ttl <= 0 {
		return fmt.Errorf("ttl must be > 0")
	}

	rec, ok, err := s.Get(ctx, deliberationID)
	if err != nil {
		return err
	}
	if !ok {
		return fmt.Errorf("deliberation not found")
	}
	if updatedAtUTC.IsZero() {
		return fmt.Errorf("updatedAtUTC cannot be zero")
	}

	rec.UpdatedAtUTC = updatedAtUTC
	payload, err := json.Marshal(rec)
	if err != nil {
		return fmt.Errorf("marshal record: %w", err)
	}

	key := s.keyRecord(deliberationID)
	if err := s.client.Set(ctx, key, payload, ttl).Err(); err != nil {
		return fmt.Errorf("redis set: %w", err)
	}
	return nil
}

func (s *RedisStore) MarkCompleted(ctx context.Context, deliberationID string, updatedAtUTC time.Time) error {
	return s.markTerminal(ctx, deliberationID, DeliberationStatusCompleted, updatedAtUTC)
}

func (s *RedisStore) MarkFailed(ctx context.Context, deliberationID string, updatedAtUTC time.Time) error {
	return s.markTerminal(ctx, deliberationID, DeliberationStatusFailed, updatedAtUTC)
}

func (s *RedisStore) markTerminal(ctx context.Context, deliberationID string, status DeliberationStatus, updatedAtUTC time.Time) error {
	if updatedAtUTC.IsZero() {
		return fmt.Errorf("updatedAtUTC cannot be zero")
	}

	rec, ok, err := s.Get(ctx, deliberationID)
	if err != nil {
		return err
	}
	if !ok {
		return fmt.Errorf("deliberation not found")
	}

	rec.Status = status
	rec.UpdatedAtUTC = updatedAtUTC
	payload, err := json.Marshal(rec)
	if err != nil {
		return fmt.Errorf("marshal record: %w", err)
	}

	key := s.keyRecord(deliberationID)
	activeKey := s.keyActiveIndex()

	// Preserve remaining TTL (do not extend). If key already has no TTL (should not happen), we keep it as-is.
	ttl, err := s.client.TTL(ctx, key).Result()
	if err != nil {
		return fmt.Errorf("redis ttl: %w", err)
	}
	if ttl <= 0 {
		// Fallback: keep a short TTL to avoid leaks.
		ttl = 10 * time.Minute
	}

	pipe := s.client.Pipeline()
	pipe.Set(ctx, key, payload, ttl)
	pipe.SRem(ctx, activeKey, deliberationID)
	_, err = pipe.Exec(ctx)
	if err != nil {
		return fmt.Errorf("redis exec: %w", err)
	}
	return nil
}

func (s *RedisStore) ListActive(ctx context.Context, limit int) ([]DeliberationRecord, error) {
	if limit <= 0 {
		limit = 100
	}

	activeKey := s.keyActiveIndex()
	ids, err := s.client.SMembers(ctx, activeKey).Result()
	if err != nil {
		return nil, fmt.Errorf("redis smembers: %w", err)
	}

	out := make([]DeliberationRecord, 0, min(len(ids), limit))

	for _, id := range ids {
		if len(out) >= limit {
			break
		}
		rec, ok, err := s.Get(ctx, id)
		if err != nil {
			return nil, err
		}
		if !ok {
			// Cleanup stale index entry.
			_ = s.client.SRem(ctx, activeKey, id).Err()
			continue
		}
		if rec.Status != DeliberationStatusRunning {
			// Defensive cleanup.
			_ = s.client.SRem(ctx, activeKey, id).Err()
			continue
		}
		out = append(out, rec)
	}

	return out, nil
}

func (s *RedisStore) keyRecord(deliberationID string) string {
	return fmt.Sprintf("%s:delib:%s", s.prefix, deliberationID)
}

func (s *RedisStore) keyActiveIndex() string {
	return fmt.Sprintf("%s:delib:active", s.prefix)
}
