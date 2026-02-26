package auth

import (
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/identity"
)

func TestAuthorizationPolicy_IsAllowed(t *testing.T) {
	t.Parallel()

	policy := NewAuthorizationPolicy()

	tests := []struct {
		name    string
		roles   []identity.Role
		method  string
		allowed bool
	}{
		// Admin: allowed for everything.
		{
			name:    "admin allowed for query (GetPlan)",
			roles:   []identity.Role{identity.RoleAdmin},
			method:  "/fleet.v1.PlanningService/GetPlan",
			allowed: true,
		},
		{
			name:    "admin allowed for command (CreateProject)",
			roles:   []identity.Role{identity.RoleAdmin},
			method:  "/fleet.v1.PlanningService/CreateProject",
			allowed: true,
		},
		{
			name:    "admin allowed for manage (ManageUsers)",
			roles:   []identity.Role{identity.RoleAdmin},
			method:  "/fleet.v1.AdminService/ManageUsers",
			allowed: true,
		},
		{
			name:    "admin allowed for delete (DeleteProject)",
			roles:   []identity.Role{identity.RoleAdmin},
			method:  "/fleet.v1.PlanningService/DeleteProject",
			allowed: true,
		},

		// Operator: queries + commands, denied management.
		{
			name:    "operator allowed for query (ListProjects)",
			roles:   []identity.Role{identity.RoleOperator},
			method:  "/fleet.v1.PlanningService/ListProjects",
			allowed: true,
		},
		{
			name:    "operator allowed for command (CreateEpic)",
			roles:   []identity.Role{identity.RoleOperator},
			method:  "/fleet.v1.PlanningService/CreateEpic",
			allowed: true,
		},
		{
			name:    "operator denied for manage (ManageUsers)",
			roles:   []identity.Role{identity.RoleOperator},
			method:  "/fleet.v1.AdminService/ManageUsers",
			allowed: false,
		},
		{
			name:    "operator denied for delete (DeleteProject)",
			roles:   []identity.Role{identity.RoleOperator},
			method:  "/fleet.v1.PlanningService/DeleteProject",
			allowed: false,
		},
		{
			name:    "operator denied for admin (AdminConfig)",
			roles:   []identity.Role{identity.RoleOperator},
			method:  "/fleet.v1.AdminService/AdminConfig",
			allowed: false,
		},

		// Viewer: queries only.
		{
			name:    "viewer allowed for query (GetCeremony)",
			roles:   []identity.Role{identity.RoleViewer},
			method:  "/fleet.v1.CeremonyService/GetCeremony",
			allowed: true,
		},
		{
			name:    "viewer allowed for list query (ListStories)",
			roles:   []identity.Role{identity.RoleViewer},
			method:  "/fleet.v1.PlanningService/ListStories",
			allowed: true,
		},
		{
			name:    "viewer allowed for watch query (WatchEvents)",
			roles:   []identity.Role{identity.RoleViewer},
			method:  "/fleet.v1.EventService/WatchEvents",
			allowed: true,
		},
		{
			name:    "viewer denied for command (CreateProject)",
			roles:   []identity.Role{identity.RoleViewer},
			method:  "/fleet.v1.PlanningService/CreateProject",
			allowed: false,
		},
		{
			name:    "viewer denied for manage (ManageUsers)",
			roles:   []identity.Role{identity.RoleViewer},
			method:  "/fleet.v1.AdminService/ManageUsers",
			allowed: false,
		},

		// Empty roles: always denied.
		{
			name:    "empty roles denied for query",
			roles:   []identity.Role{},
			method:  "/fleet.v1.PlanningService/GetPlan",
			allowed: false,
		},
		{
			name:    "nil roles denied for command",
			roles:   nil,
			method:  "/fleet.v1.PlanningService/CreateProject",
			allowed: false,
		},

		// Multiple roles: highest privilege wins.
		{
			name:    "viewer+admin allowed for manage",
			roles:   []identity.Role{identity.RoleViewer, identity.RoleAdmin},
			method:  "/fleet.v1.AdminService/ManageUsers",
			allowed: true,
		},
		{
			name:    "viewer+operator allowed for command",
			roles:   []identity.Role{identity.RoleViewer, identity.RoleOperator},
			method:  "/fleet.v1.PlanningService/CreateProject",
			allowed: true,
		},

		// Method without service prefix.
		{
			name:    "bare method name classified as command",
			roles:   []identity.Role{identity.RoleOperator},
			method:  "StartCeremony",
			allowed: true,
		},
		{
			name:    "bare query method name",
			roles:   []identity.Role{identity.RoleViewer},
			method:  "QueryMetrics",
			allowed: true,
		},

		// Config classified as manage.
		{
			name:    "operator denied for config method",
			roles:   []identity.Role{identity.RoleOperator},
			method:  "/fleet.v1.AdminService/ConfigUpdate",
			allowed: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			got := policy.IsAllowed(tt.roles, tt.method)
			if got != tt.allowed {
				t.Errorf("IsAllowed(%v, %q) = %v, want %v", tt.roles, tt.method, got, tt.allowed)
			}
		})
	}
}
