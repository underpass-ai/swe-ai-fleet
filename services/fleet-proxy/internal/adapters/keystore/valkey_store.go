// Package keystore provides the API key validation adapter implementing
// ports.ApiKeyStore. The real implementation will connect to Valkey/Redis.
package keystore

import (
	"context"
	"fmt"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/identity"
)

// ValkeyStore implements ports.ApiKeyStore backed by a Valkey/Redis instance.
// Currently a stub that will be connected in Phase 2.
type ValkeyStore struct {
	addr string
}

// NewValkeyStore creates a ValkeyStore targeting the given address.
func NewValkeyStore(addr string) *ValkeyStore {
	return &ValkeyStore{addr: addr}
}

// Validate checks the keyID/secret pair against the store. Currently returns
// an error because the Valkey connection is not yet established.
func (s *ValkeyStore) Validate(_ context.Context, _, _ string) (identity.ClientID, error) {
	return identity.ClientID{}, fmt.Errorf("valkey store not connected to %s", s.addr)
}
