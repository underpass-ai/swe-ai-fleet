package auth

import (
	"strings"
	"testing"
)

func TestParseScope(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name      string
		input     string
		wantScope Scope
		wantErr   bool
		errSubstr string
	}{
		{
			name:      "watch",
			input:     "watch",
			wantScope: ScopeWatch,
		},
		{
			name:      "approve",
			input:     "approve",
			wantScope: ScopeApprove,
		},
		{
			name:      "start",
			input:     "start",
			wantScope: ScopeStart,
		},
		{
			name:      "manage",
			input:     "manage",
			wantScope: ScopeManage,
		},
		{
			name:      "empty string",
			input:     "",
			wantErr:   true,
			errSubstr: "cannot be empty",
		},
		{
			name:      "delete is invalid",
			input:     "delete",
			wantErr:   true,
			errSubstr: "unknown scope",
		},
		{
			name:      "admin is invalid",
			input:     "admin",
			wantErr:   true,
			errSubstr: "unknown scope",
		},
		{
			name:      "uppercase is invalid",
			input:     "Watch",
			wantErr:   true,
			errSubstr: "unknown scope",
		},
		{
			name:      "execute is invalid",
			input:     "execute",
			wantErr:   true,
			errSubstr: "unknown scope",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			got, err := ParseScope(tt.input)

			if tt.wantErr {
				if err == nil {
					t.Fatalf("ParseScope(%q) expected error containing %q, got nil", tt.input, tt.errSubstr)
				}
				if !strings.Contains(err.Error(), tt.errSubstr) {
					t.Fatalf("ParseScope(%q) error = %q, want substring %q", tt.input, err.Error(), tt.errSubstr)
				}
				return
			}

			if err != nil {
				t.Fatalf("ParseScope(%q) unexpected error: %v", tt.input, err)
			}

			if got != tt.wantScope {
				t.Errorf("ParseScope(%q) = %v, want %v", tt.input, got, tt.wantScope)
			}
		})
	}
}

func TestScope_IsValid(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name  string
		scope Scope
		valid bool
	}{
		{"watch is valid", ScopeWatch, true},
		{"approve is valid", ScopeApprove, true},
		{"start is valid", ScopeStart, true},
		{"manage is valid", ScopeManage, true},
		{"zero is invalid", Scope(0), false},
		{"255 is invalid", Scope(255), false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			if got := tt.scope.IsValid(); got != tt.valid {
				t.Errorf("Scope(%d).IsValid() = %v, want %v", tt.scope, got, tt.valid)
			}
		})
	}
}

func TestScope_String(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name  string
		scope Scope
		want  string
	}{
		{"watch", ScopeWatch, "watch"},
		{"approve", ScopeApprove, "approve"},
		{"start", ScopeStart, "start"},
		{"manage", ScopeManage, "manage"},
		{"unknown scope", Scope(99), "unknown"},
		{"zero scope", Scope(0), "unknown"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			if got := tt.scope.String(); got != tt.want {
				t.Errorf("Scope(%d).String() = %q, want %q", tt.scope, got, tt.want)
			}
		})
	}
}
