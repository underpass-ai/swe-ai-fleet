// Package identitymap provides an in-memory identity resolver implementing
// ports.IdentityResolver. It maps known client IDs to their roles and scopes
// using a static configuration.
package identitymap

import (
	"context"
	"fmt"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/auth"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/identity"
)

// resolvedIdentity holds the roles and scopes for a client.
type resolvedIdentity struct {
	roles  []identity.Role
	scopes []auth.Scope
}

// ConfigResolver is a static identity resolver that uses an in-memory mapping
// from client ID string to roles and scopes.
type ConfigResolver struct {
	mapping map[string]resolvedIdentity
}

// NewConfigResolver creates a ConfigResolver with a default admin mapping.
// The default admin identity is spiffe://swe-ai-fleet/user/admin/device/cli
// with all roles and all scopes.
func NewConfigResolver() *ConfigResolver {
	return &ConfigResolver{
		mapping: map[string]resolvedIdentity{
			"spiffe://swe-ai-fleet/user/admin/device/cli": {
				roles: []identity.Role{
					identity.RoleAdmin,
					identity.RoleOperator,
					identity.RoleViewer,
				},
				scopes: []auth.Scope{
					auth.ScopeWatch,
					auth.ScopeApprove,
					auth.ScopeStart,
					auth.ScopeManage,
				},
			},
		},
	}
}

// AddMapping registers a client identity with the given roles and scopes.
// If the client ID already exists, it is overwritten.
func (r *ConfigResolver) AddMapping(clientID string, roles []identity.Role, scopes []auth.Scope) {
	r.mapping[clientID] = resolvedIdentity{
		roles:  roles,
		scopes: scopes,
	}
}

// Resolve returns the roles and scopes granted to the given client.
// If the client ID is not found in the mapping, an error is returned.
func (r *ConfigResolver) Resolve(_ context.Context, clientID identity.ClientID) ([]identity.Role, []auth.Scope, error) {
	id, ok := r.mapping[clientID.String()]
	if !ok {
		return nil, nil, fmt.Errorf("identity %q not found in config map", clientID.String())
	}
	return id.roles, id.scopes, nil
}
