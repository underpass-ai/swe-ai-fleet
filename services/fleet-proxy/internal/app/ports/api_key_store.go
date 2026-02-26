package ports

import (
	"context"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/identity"
)

// ApiKeyStore is a port for validating API key credentials during the
// enrollment flow. The adapter may back this with Valkey/Redis, a database,
// or a static configuration.
type ApiKeyStore interface {
	// Validate checks the keyID/secret pair. On success it returns the
	// ClientID associated with that API key. On failure it returns an error.
	Validate(ctx context.Context, keyID string, secret string) (identity.ClientID, error)
}
