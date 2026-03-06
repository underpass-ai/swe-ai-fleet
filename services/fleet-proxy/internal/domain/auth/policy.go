package auth

import (
	"strings"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/identity"
)

// methodCategory classifies an RPC method by its access pattern.
type methodCategory int

const (
	categoryQuery   methodCategory = iota // read-only operations
	categoryCommand                       // state-changing operations
	categoryManage                        // administrative operations
)

// AuthorizationPolicy is a domain service that determines whether a set of
// roles is allowed to invoke a given RPC method. It uses convention-based
// method classification:
//
//   - Methods containing "Get", "List", "Watch", or "Query" are queries.
//   - Methods containing "Manage", "Delete", "Admin", or "Config" are management.
//   - All other methods are commands.
//
// Role-to-category mapping:
//   - Admin:    queries + commands + management (everything)
//   - Operator: queries + commands
//   - Viewer:   queries only
type AuthorizationPolicy struct{}

// NewAuthorizationPolicy creates a new AuthorizationPolicy.
func NewAuthorizationPolicy() AuthorizationPolicy {
	return AuthorizationPolicy{}
}

// IsAllowed reports whether any of the provided roles grants access to the
// given RPC method. If roles is empty, access is denied. The method string
// is typically a fully-qualified gRPC method name (e.g., "/fleet.v1.PlanningService/GetPlan").
func (p AuthorizationPolicy) IsAllowed(roles []identity.Role, method string) bool {
	if len(roles) == 0 {
		return false
	}

	cat := classifyMethod(method)
	for _, role := range roles {
		if roleAllowsCategory(role, cat) {
			return true
		}
	}

	return false
}

// classifyMethod determines the category of an RPC method based on naming
// conventions in the method path.
func classifyMethod(method string) methodCategory {
	// Extract the method name after the last '/' for pattern matching.
	name := method
	if idx := strings.LastIndex(method, "/"); idx >= 0 {
		name = method[idx+1:]
	}

	// Management methods (most restrictive, check first).
	managePatterns := []string{"Manage", "Delete", "Admin", "Config"}
	for _, pat := range managePatterns {
		if strings.Contains(name, pat) {
			return categoryManage
		}
	}

	// Query methods (read-only).
	queryPatterns := []string{"Get", "List", "Watch", "Query"}
	for _, pat := range queryPatterns {
		if strings.Contains(name, pat) {
			return categoryQuery
		}
	}

	// Default: commands (state-changing operations).
	return categoryCommand
}

// roleAllowsCategory checks if a single role grants access to a method category.
func roleAllowsCategory(role identity.Role, cat methodCategory) bool {
	switch role {
	case identity.RoleAdmin:
		// Admin can do everything.
		return true
	case identity.RoleOperator:
		// Operator can do commands and queries, but not management.
		return cat == categoryCommand || cat == categoryQuery
	case identity.RoleViewer:
		// Viewer can only read.
		return cat == categoryQuery
	default:
		return false
	}
}
