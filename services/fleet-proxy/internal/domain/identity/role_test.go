package identity

import (
	"strings"
	"testing"
)

func TestParseRole(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name      string
		input     string
		wantRole  Role
		wantErr   bool
		errSubstr string
	}{
		{
			name:     "viewer",
			input:    "viewer",
			wantRole: RoleViewer,
		},
		{
			name:     "operator",
			input:    "operator",
			wantRole: RoleOperator,
		},
		{
			name:     "admin",
			input:    "admin",
			wantRole: RoleAdmin,
		},
		{
			name:      "empty string",
			input:     "",
			wantErr:   true,
			errSubstr: "cannot be empty",
		},
		{
			name:      "superadmin is invalid",
			input:     "superadmin",
			wantErr:   true,
			errSubstr: "unknown role",
		},
		{
			name:      "root is invalid",
			input:     "root",
			wantErr:   true,
			errSubstr: "unknown role",
		},
		{
			name:      "uppercase is invalid",
			input:     "Admin",
			wantErr:   true,
			errSubstr: "unknown role",
		},
		{
			name:      "mixed case is invalid",
			input:     "Viewer",
			wantErr:   true,
			errSubstr: "unknown role",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			got, err := ParseRole(tt.input)

			if tt.wantErr {
				if err == nil {
					t.Fatalf("ParseRole(%q) expected error containing %q, got nil", tt.input, tt.errSubstr)
				}
				if !strings.Contains(err.Error(), tt.errSubstr) {
					t.Fatalf("ParseRole(%q) error = %q, want substring %q", tt.input, err.Error(), tt.errSubstr)
				}
				return
			}

			if err != nil {
				t.Fatalf("ParseRole(%q) unexpected error: %v", tt.input, err)
			}

			if got != tt.wantRole {
				t.Errorf("ParseRole(%q) = %v, want %v", tt.input, got, tt.wantRole)
			}
		})
	}
}

func TestRole_IsValid(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name  string
		role  Role
		valid bool
	}{
		{"viewer is valid", RoleViewer, true},
		{"operator is valid", RoleOperator, true},
		{"admin is valid", RoleAdmin, true},
		{"zero is invalid", Role(0), false},
		{"255 is invalid", Role(255), false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			if got := tt.role.IsValid(); got != tt.valid {
				t.Errorf("Role(%d).IsValid() = %v, want %v", tt.role, got, tt.valid)
			}
		})
	}
}

func TestRole_String(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name string
		role Role
		want string
	}{
		{"viewer", RoleViewer, "viewer"},
		{"operator", RoleOperator, "operator"},
		{"admin", RoleAdmin, "admin"},
		{"unknown role", Role(99), "unknown"},
		{"zero role", Role(0), "unknown"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			if got := tt.role.String(); got != tt.want {
				t.Errorf("Role(%d).String() = %q, want %q", tt.role, got, tt.want)
			}
		})
	}
}
