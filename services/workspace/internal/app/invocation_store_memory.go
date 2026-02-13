package app

import (
	"context"
	"sync"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
)

type InMemoryInvocationStore struct {
	mu          sync.RWMutex
	invocations map[string]domain.Invocation
}

func NewInMemoryInvocationStore() *InMemoryInvocationStore {
	return &InMemoryInvocationStore{
		invocations: map[string]domain.Invocation{},
	}
}

func (s *InMemoryInvocationStore) Save(_ context.Context, invocation domain.Invocation) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.invocations[invocation.ID] = invocation
	return nil
}

func (s *InMemoryInvocationStore) Get(_ context.Context, invocationID string) (domain.Invocation, bool, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	invocation, ok := s.invocations[invocationID]
	return invocation, ok, nil
}
