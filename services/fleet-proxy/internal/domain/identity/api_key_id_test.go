package identity

import (
	"strings"
	"testing"
)

func TestNewApiKeyID(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name      string
		raw       string
		wantErr   bool
		errSubstr string
	}{
		{
			name: "valid UUID",
			raw:  "550e8400-e29b-41d4-a716-446655440000",
		},
		{
			name: "valid UUID uppercase",
			raw:  "550E8400-E29B-41D4-A716-446655440000",
		},
		{
			name: "valid UUID mixed case",
			raw:  "550e8400-E29B-41d4-a716-446655440000",
		},
		{
			name:      "empty string",
			raw:       "",
			wantErr:   true,
			errSubstr: "cannot be empty",
		},
		{
			name:      "not a UUID",
			raw:       "not-a-uuid",
			wantErr:   true,
			errSubstr: "must be a valid UUID",
		},
		{
			name:      "truncated UUID",
			raw:       "550e8400",
			wantErr:   true,
			errSubstr: "must be a valid UUID",
		},
		{
			name:      "UUID without dashes",
			raw:       "550e8400e29b41d4a716446655440000",
			wantErr:   true,
			errSubstr: "must be a valid UUID",
		},
		{
			name:      "UUID with extra chars",
			raw:       "550e8400-e29b-41d4-a716-446655440000-extra",
			wantErr:   true,
			errSubstr: "must be a valid UUID",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			kid, err := NewApiKeyID(tt.raw)

			if tt.wantErr {
				if err == nil {
					t.Fatalf("NewApiKeyID(%q) expected error containing %q, got nil", tt.raw, tt.errSubstr)
				}
				if !strings.Contains(err.Error(), tt.errSubstr) {
					t.Fatalf("NewApiKeyID(%q) error = %q, want substring %q", tt.raw, err.Error(), tt.errSubstr)
				}
				return
			}

			if err != nil {
				t.Fatalf("NewApiKeyID(%q) unexpected error: %v", tt.raw, err)
			}

			if kid.String() != tt.raw {
				t.Errorf("String() = %q, want %q", kid.String(), tt.raw)
			}

			if kid.IsZero() {
				t.Error("IsZero() = true for valid ApiKeyID, want false")
			}
		})
	}
}

func TestApiKeyID_IsZero(t *testing.T) {
	t.Parallel()

	var zero ApiKeyID
	if !zero.IsZero() {
		t.Error("IsZero() = false for zero-value ApiKeyID, want true")
	}

	if zero.String() != "" {
		t.Errorf("String() = %q for zero-value ApiKeyID, want empty", zero.String())
	}
}
