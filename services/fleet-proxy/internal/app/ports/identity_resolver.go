package ports

import (
	"context"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/auth"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/identity"
)

// IdentityResolver is a port for mapping a ClientID to its roles and scopes.
// This is used during mTLS authentication to populate the authorization context.
type IdentityResolver interface {
	// Resolve returns the roles and scopes granted to the given client.
	Resolve(ctx context.Context, clientID identity.ClientID) ([]identity.Role, []auth.Scope, error)
}
