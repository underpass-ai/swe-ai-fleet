package invocationstore

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	redis "github.com/redis/go-redis/v9"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
)

type valkeyClient interface {
	Ping(ctx context.Context) *redis.StatusCmd
	Set(ctx context.Context, key string, value interface{}, expiration time.Duration) *redis.StatusCmd
	Get(ctx context.Context, key string) *redis.StringCmd
}

type ValkeyStore struct {
	client    valkeyClient
	keyPrefix string
	ttl       time.Duration
}

func NewValkeyStore(client valkeyClient, keyPrefix string, ttl time.Duration) *ValkeyStore {
	prefix := strings.TrimSpace(keyPrefix)
	if prefix == "" {
		prefix = "workspace:invocation"
	}
	return &ValkeyStore{
		client:    client,
		keyPrefix: prefix,
		ttl:       ttl,
	}
}

func NewValkeyStoreFromAddress(
	ctx context.Context,
	address string,
	password string,
	db int,
	keyPrefix string,
	ttl time.Duration,
) (*ValkeyStore, error) {
	client := redis.NewClient(&redis.Options{
		Addr:     strings.TrimSpace(address),
		Password: password,
		DB:       db,
	})
	if err := client.Ping(ctx).Err(); err != nil {
		return nil, fmt.Errorf("valkey ping failed: %w", err)
	}
	return NewValkeyStore(client, keyPrefix, ttl), nil
}

func (s *ValkeyStore) Save(ctx context.Context, invocation domain.Invocation) error {
	data, err := json.Marshal(invocation)
	if err != nil {
		return fmt.Errorf("marshal invocation: %w", err)
	}

	key := s.key(invocation.ID)
	if s.ttl > 0 {
		if err := s.client.Set(ctx, key, data, s.ttl).Err(); err != nil {
			return fmt.Errorf("set invocation: %w", err)
		}
		return nil
	}
	if err := s.client.Set(ctx, key, data, 0).Err(); err != nil {
		return fmt.Errorf("set invocation: %w", err)
	}
	return nil
}

func (s *ValkeyStore) Get(ctx context.Context, invocationID string) (domain.Invocation, bool, error) {
	result, err := s.client.Get(ctx, s.key(invocationID)).Result()
	if err != nil {
		if err == redis.Nil {
			return domain.Invocation{}, false, nil
		}
		return domain.Invocation{}, false, fmt.Errorf("get invocation: %w", err)
	}

	var invocation domain.Invocation
	if err := json.Unmarshal([]byte(result), &invocation); err != nil {
		return domain.Invocation{}, false, fmt.Errorf("unmarshal invocation: %w", err)
	}
	return invocation, true, nil
}

func (s *ValkeyStore) key(invocationID string) string {
	return s.keyPrefix + ":" + invocationID
}
