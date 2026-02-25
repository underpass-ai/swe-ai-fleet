// Package keystore provides API key validation adapters implementing
// ports.ApiKeyStore.
package keystore

import (
	"context"
	"fmt"
	"strings"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/identity"
)

// StaticEntry holds a parsed API key entry from the static configuration.
type StaticEntry struct {
	KeyID    string
	Secret   string
	UserID   string
	DeviceID string
	ClientID identity.ClientID
}

// StaticStore implements ports.ApiKeyStore using environment-variable-based
// static API keys. Intended for development and E2E testing where Valkey
// is not available.
//
// Config format: "keyID:secret:userID:deviceID[;keyID:secret:userID:deviceID;...]"
type StaticStore struct {
	entries map[string]StaticEntry // keyed by keyID
}

// NewStaticStore parses the config string and returns a StaticStore.
// Each entry is "keyID:secret:userID:deviceID" separated by semicolons.
// Returns an error if any entry is malformed or produces an invalid SPIFFE URI.
func NewStaticStore(config string) (*StaticStore, error) {
	if strings.TrimSpace(config) == "" {
		return nil, fmt.Errorf("static API keys config is empty")
	}

	entries := make(map[string]StaticEntry)
	parts := strings.Split(config, ";")

	for _, part := range parts {
		part = strings.TrimSpace(part)
		if part == "" {
			continue
		}

		fields := strings.SplitN(part, ":", 4)
		if len(fields) != 4 {
			return nil, fmt.Errorf("malformed static API key entry %q: expected keyID:secret:userID:deviceID", part)
		}

		keyID, secret, userID, deviceID := fields[0], fields[1], fields[2], fields[3]
		if keyID == "" || secret == "" || userID == "" || deviceID == "" {
			return nil, fmt.Errorf("malformed static API key entry %q: all fields must be non-empty", part)
		}

		spiffeURI := fmt.Sprintf("spiffe://swe-ai-fleet/user/%s/device/%s", userID, deviceID)
		clientID, err := identity.NewClientID(spiffeURI)
		if err != nil {
			return nil, fmt.Errorf("invalid identity for entry %q: %w", keyID, err)
		}

		entries[keyID] = StaticEntry{
			KeyID:    keyID,
			Secret:   secret,
			UserID:   userID,
			DeviceID: deviceID,
			ClientID: clientID,
		}
	}

	if len(entries) == 0 {
		return nil, fmt.Errorf("static API keys config produced no valid entries")
	}

	return &StaticStore{entries: entries}, nil
}

// Validate checks the keyID/secret pair against the static store.
func (s *StaticStore) Validate(_ context.Context, keyID, secret string) (identity.ClientID, error) {
	entry, ok := s.entries[keyID]
	if !ok {
		return identity.ClientID{}, fmt.Errorf("unknown API key ID %q", keyID)
	}
	if entry.Secret != secret {
		return identity.ClientID{}, fmt.Errorf("invalid secret for API key %q", keyID)
	}
	return entry.ClientID, nil
}

// Entries returns all registered static entries. This allows callers
// (e.g. main.go) to bootstrap identity mappings for each entry.
func (s *StaticStore) Entries() []StaticEntry {
	result := make([]StaticEntry, 0, len(s.entries))
	for _, e := range s.entries {
		result = append(result, e)
	}
	return result
}
