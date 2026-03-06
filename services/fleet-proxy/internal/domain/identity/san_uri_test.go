package identity

import (
	"strings"
	"testing"
)

func TestNewSANUri(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name      string
		raw       string
		wantErr   bool
		errSubstr string
	}{
		{
			name: "valid spiffe URI",
			raw:  "spiffe://swe-ai-fleet/user/tirso/device/macbook",
		},
		{
			name: "valid https URI",
			raw:  "https://example.com/path",
		},
		{
			name: "valid http URI",
			raw:  "http://localhost:8080/status",
		},
		{
			name:      "empty string",
			raw:       "",
			wantErr:   true,
			errSubstr: "cannot be empty",
		},
		{
			name:      "no scheme",
			raw:       "example.com",
			wantErr:   true,
			errSubstr: "missing scheme",
		},
		{
			name:      "whitespace only",
			raw:       "   ",
			wantErr:   true,
			errSubstr: "missing scheme",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			san, err := NewSANUri(tt.raw)

			if tt.wantErr {
				if err == nil {
					t.Fatalf("NewSANUri(%q) expected error containing %q, got nil", tt.raw, tt.errSubstr)
				}
				if !strings.Contains(err.Error(), tt.errSubstr) {
					t.Fatalf("NewSANUri(%q) error = %q, want substring %q", tt.raw, err.Error(), tt.errSubstr)
				}
				return
			}

			if err != nil {
				t.Fatalf("NewSANUri(%q) unexpected error: %v", tt.raw, err)
			}

			if san.String() != tt.raw {
				t.Errorf("String() = %q, want %q", san.String(), tt.raw)
			}

			if san.IsZero() {
				t.Error("IsZero() = true for valid SANUri, want false")
			}
		})
	}
}

func TestSANUri_IsZero(t *testing.T) {
	t.Parallel()

	var zero SANUri
	if !zero.IsZero() {
		t.Error("IsZero() = false for zero-value SANUri, want true")
	}

	if zero.String() != "" {
		t.Errorf("String() = %q for zero-value SANUri, want empty", zero.String())
	}
}
