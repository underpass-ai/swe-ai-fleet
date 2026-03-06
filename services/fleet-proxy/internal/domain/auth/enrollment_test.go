package auth

import (
	"crypto/sha256"
	"strings"
	"testing"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/identity"
)

func mustSANUri(t *testing.T, raw string) identity.SANUri {
	t.Helper()
	san, err := identity.NewSANUri(raw)
	if err != nil {
		t.Fatalf("mustSANUri(%q): %v", raw, err)
	}
	return san
}

func mustApiKeyID(t *testing.T, raw string) identity.ApiKeyID {
	t.Helper()
	kid, err := identity.NewApiKeyID(raw)
	if err != nil {
		t.Fatalf("mustApiKeyID(%q): %v", raw, err)
	}
	return kid
}

func TestNewEnrollmentRequest(t *testing.T) {
	t.Parallel()

	validCSR := []byte("-----BEGIN CERTIFICATE REQUEST-----\nfake-csr-data\n-----END CERTIFICATE REQUEST-----\n")
	validSAN := mustSANUri(t, "spiffe://swe-ai-fleet/user/tirso/device/macbook")
	validKeyID := mustApiKeyID(t, "550e8400-e29b-41d4-a716-446655440000")

	tests := []struct {
		name      string
		csr       []byte
		san       identity.SANUri
		keyID     identity.ApiKeyID
		wantErr   bool
		errSubstr string
	}{
		{
			name:  "valid enrollment request",
			csr:   validCSR,
			san:   validSAN,
			keyID: validKeyID,
		},
		{
			name:      "empty CSR",
			csr:       nil,
			san:       validSAN,
			keyID:     validKeyID,
			wantErr:   true,
			errSubstr: "CSR cannot be empty",
		},
		{
			name:      "zero-length CSR",
			csr:       []byte{},
			san:       validSAN,
			keyID:     validKeyID,
			wantErr:   true,
			errSubstr: "CSR cannot be empty",
		},
		{
			name:      "zero SANUri",
			csr:       validCSR,
			san:       identity.SANUri{},
			keyID:     validKeyID,
			wantErr:   true,
			errSubstr: "requested identity cannot be empty",
		},
		{
			name:      "zero ApiKeyID",
			csr:       validCSR,
			san:       validSAN,
			keyID:     identity.ApiKeyID{},
			wantErr:   true,
			errSubstr: "API key ID cannot be empty",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			before := time.Now()
			req, err := NewEnrollmentRequest(tt.csr, tt.san, tt.keyID)
			after := time.Now()

			if tt.wantErr {
				if err == nil {
					t.Fatalf("NewEnrollmentRequest() expected error containing %q, got nil", tt.errSubstr)
				}
				if !strings.Contains(err.Error(), tt.errSubstr) {
					t.Fatalf("NewEnrollmentRequest() error = %q, want substring %q", err.Error(), tt.errSubstr)
				}
				return
			}

			if err != nil {
				t.Fatalf("NewEnrollmentRequest() unexpected error: %v", err)
			}

			// Verify fields.
			if string(req.CSR) != string(tt.csr) {
				t.Errorf("CSR = %q, want %q", req.CSR, tt.csr)
			}

			if req.RequestedIdentity.String() != tt.san.String() {
				t.Errorf("RequestedIdentity = %q, want %q", req.RequestedIdentity.String(), tt.san.String())
			}

			if req.ApiKeyID.String() != tt.keyID.String() {
				t.Errorf("ApiKeyID = %q, want %q", req.ApiKeyID.String(), tt.keyID.String())
			}

			// Verify CSRHash is SHA-256 of CSR.
			expectedHash := sha256.Sum256(tt.csr)
			if req.CSRHash != expectedHash {
				t.Errorf("CSRHash = %x, want %x", req.CSRHash, expectedHash)
			}

			// Verify RequestedAt is set to approximately now.
			if req.RequestedAt.Before(before) || req.RequestedAt.After(after) {
				t.Errorf("RequestedAt = %v, want between %v and %v", req.RequestedAt, before, after)
			}
		})
	}
}
