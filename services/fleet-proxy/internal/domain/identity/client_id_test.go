package identity

import (
	"strings"
	"testing"
)

func TestNewClientID(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name      string
		raw       string
		wantErr   bool
		errSubstr string
		wantUser  string
		wantDev   string
	}{
		{
			name:     "valid SPIFFE URI",
			raw:      "spiffe://swe-ai-fleet/user/tirso/device/macbook",
			wantUser: "tirso",
			wantDev:  "macbook",
		},
		{
			name:     "valid with hyphens and underscores",
			raw:      "spiffe://swe-ai-fleet/user/user-one_2/device/dev_3-x",
			wantUser: "user-one_2",
			wantDev:  "dev_3-x",
		},
		{
			name:     "valid with numeric segments",
			raw:      "spiffe://swe-ai-fleet/user/12345/device/67890",
			wantUser: "12345",
			wantDev:  "67890",
		},
		{
			name:      "empty string",
			raw:       "",
			wantErr:   true,
			errSubstr: "cannot be empty",
		},
		{
			name:      "missing scheme",
			raw:       "swe-ai-fleet/user/tirso/device/macbook",
			wantErr:   true,
			errSubstr: "invalid SPIFFE URI",
		},
		{
			name:      "wrong scheme",
			raw:       "https://swe-ai-fleet/user/tirso/device/macbook",
			wantErr:   true,
			errSubstr: "invalid SPIFFE URI",
		},
		{
			name:      "wrong trust domain",
			raw:       "spiffe://other-domain/user/tirso/device/macbook",
			wantErr:   true,
			errSubstr: "invalid SPIFFE URI",
		},
		{
			name:      "missing device segment",
			raw:       "spiffe://swe-ai-fleet/user/tirso",
			wantErr:   true,
			errSubstr: "invalid SPIFFE URI",
		},
		{
			name:      "missing user segment",
			raw:       "spiffe://swe-ai-fleet/device/macbook",
			wantErr:   true,
			errSubstr: "invalid SPIFFE URI",
		},
		{
			name:      "empty user ID",
			raw:       "spiffe://swe-ai-fleet/user//device/macbook",
			wantErr:   true,
			errSubstr: "invalid SPIFFE URI",
		},
		{
			name:      "empty device ID",
			raw:       "spiffe://swe-ai-fleet/user/tirso/device/",
			wantErr:   true,
			errSubstr: "invalid SPIFFE URI",
		},
		{
			name:      "trailing slash",
			raw:       "spiffe://swe-ai-fleet/user/tirso/device/macbook/",
			wantErr:   true,
			errSubstr: "invalid SPIFFE URI",
		},
		{
			name:      "extra path segment",
			raw:       "spiffe://swe-ai-fleet/user/tirso/device/macbook/extra",
			wantErr:   true,
			errSubstr: "invalid SPIFFE URI",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			got, err := NewClientID(tt.raw)

			if tt.wantErr {
				if err == nil {
					t.Fatalf("NewClientID(%q) expected error containing %q, got nil", tt.raw, tt.errSubstr)
				}
				if !strings.Contains(err.Error(), tt.errSubstr) {
					t.Fatalf("NewClientID(%q) error = %q, want substring %q", tt.raw, err.Error(), tt.errSubstr)
				}
				return
			}

			if err != nil {
				t.Fatalf("NewClientID(%q) unexpected error: %v", tt.raw, err)
			}

			if got.String() != tt.raw {
				t.Errorf("String() = %q, want %q", got.String(), tt.raw)
			}
			if got.UserID() != tt.wantUser {
				t.Errorf("UserID() = %q, want %q", got.UserID(), tt.wantUser)
			}
			if got.DeviceID() != tt.wantDev {
				t.Errorf("DeviceID() = %q, want %q", got.DeviceID(), tt.wantDev)
			}
			if got.IsZero() {
				t.Error("IsZero() = true, want false for a valid ClientID")
			}
		})
	}
}

func TestClientID_IsZero(t *testing.T) {
	t.Parallel()

	var zero ClientID
	if !zero.IsZero() {
		t.Error("zero-value ClientID: IsZero() = false, want true")
	}

	valid, err := NewClientID("spiffe://swe-ai-fleet/user/tirso/device/macbook")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if valid.IsZero() {
		t.Error("valid ClientID: IsZero() = true, want false")
	}
}

func TestClientID_String_ZeroValue(t *testing.T) {
	t.Parallel()

	var zero ClientID
	if zero.String() != "" {
		t.Errorf("zero-value String() = %q, want empty string", zero.String())
	}
}
