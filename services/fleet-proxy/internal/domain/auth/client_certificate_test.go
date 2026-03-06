package auth

import (
	"strings"
	"testing"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/identity"
)

func mustClientID(t *testing.T, raw string) identity.ClientID {
	t.Helper()
	cid, err := identity.NewClientID(raw)
	if err != nil {
		t.Fatalf("mustClientID(%q): %v", raw, err)
	}
	return cid
}

// validCertFields returns a complete set of valid fields for NewClientCertificate.
func validCertFields(t *testing.T) (
	identity.ClientID,
	identity.SANUri,
	[]identity.Role,
	time.Time,
	time.Time,
	string,
	identity.CertFingerprint,
) {
	t.Helper()
	clientID := mustClientID(t, "spiffe://swe-ai-fleet/user/tirso/device/macbook")
	sanURI := mustSANUri(t, "spiffe://swe-ai-fleet/user/tirso/device/macbook")
	roles := []identity.Role{identity.RoleOperator}
	issuedAt := time.Now()
	expiresAt := issuedAt.Add(24 * time.Hour)
	serial := "abc123serial"
	fp := identity.NewCertFingerprint([]byte("fake-der-bytes"))
	return clientID, sanURI, roles, issuedAt, expiresAt, serial, fp
}

func TestNewClientCertificate(t *testing.T) {
	t.Parallel()

	clientID, sanURI, roles, issuedAt, expiresAt, serial, fp := validCertFields(t)

	tests := []struct {
		name        string
		clientID    identity.ClientID
		sanURI      identity.SANUri
		roles       []identity.Role
		issuedAt    time.Time
		expiresAt   time.Time
		serial      string
		fingerprint identity.CertFingerprint
		wantErr     bool
		errSubstr   string
	}{
		{
			name:        "valid certificate",
			clientID:    clientID,
			sanURI:      sanURI,
			roles:       roles,
			issuedAt:    issuedAt,
			expiresAt:   expiresAt,
			serial:      serial,
			fingerprint: fp,
		},
		{
			name:        "zero client ID",
			clientID:    identity.ClientID{},
			sanURI:      sanURI,
			roles:       roles,
			issuedAt:    issuedAt,
			expiresAt:   expiresAt,
			serial:      serial,
			fingerprint: fp,
			wantErr:     true,
			errSubstr:   "client ID cannot be empty",
		},
		{
			name:        "zero SAN URI",
			clientID:    clientID,
			sanURI:      identity.SANUri{},
			roles:       roles,
			issuedAt:    issuedAt,
			expiresAt:   expiresAt,
			serial:      serial,
			fingerprint: fp,
			wantErr:     true,
			errSubstr:   "SAN URI cannot be empty",
		},
		{
			name:        "empty roles",
			clientID:    clientID,
			sanURI:      sanURI,
			roles:       []identity.Role{},
			issuedAt:    issuedAt,
			expiresAt:   expiresAt,
			serial:      serial,
			fingerprint: fp,
			wantErr:     true,
			errSubstr:   "at least one role is required",
		},
		{
			name:        "nil roles",
			clientID:    clientID,
			sanURI:      sanURI,
			roles:       nil,
			issuedAt:    issuedAt,
			expiresAt:   expiresAt,
			serial:      serial,
			fingerprint: fp,
			wantErr:     true,
			errSubstr:   "at least one role is required",
		},
		{
			name:        "invalid role",
			clientID:    clientID,
			sanURI:      sanURI,
			roles:       []identity.Role{identity.Role(99)},
			issuedAt:    issuedAt,
			expiresAt:   expiresAt,
			serial:      serial,
			fingerprint: fp,
			wantErr:     true,
			errSubstr:   "invalid role",
		},
		{
			name:        "empty serial",
			clientID:    clientID,
			sanURI:      sanURI,
			roles:       roles,
			issuedAt:    issuedAt,
			expiresAt:   expiresAt,
			serial:      "",
			fingerprint: fp,
			wantErr:     true,
			errSubstr:   "serial cannot be empty",
		},
		{
			name:        "zero fingerprint",
			clientID:    clientID,
			sanURI:      sanURI,
			roles:       roles,
			issuedAt:    issuedAt,
			expiresAt:   expiresAt,
			serial:      serial,
			fingerprint: identity.CertFingerprint{},
			wantErr:     true,
			errSubstr:   "fingerprint cannot be zero",
		},
		{
			name:        "expiresAt before issuedAt",
			clientID:    clientID,
			sanURI:      sanURI,
			roles:       roles,
			issuedAt:    issuedAt,
			expiresAt:   issuedAt.Add(-1 * time.Hour),
			serial:      serial,
			fingerprint: fp,
			wantErr:     true,
			errSubstr:   "expiresAt must be after issuedAt",
		},
		{
			name:        "expiresAt equals issuedAt",
			clientID:    clientID,
			sanURI:      sanURI,
			roles:       roles,
			issuedAt:    issuedAt,
			expiresAt:   issuedAt,
			serial:      serial,
			fingerprint: fp,
			wantErr:     true,
			errSubstr:   "expiresAt must be after issuedAt",
		},
		{
			name:        "multiple valid roles",
			clientID:    clientID,
			sanURI:      sanURI,
			roles:       []identity.Role{identity.RoleViewer, identity.RoleOperator, identity.RoleAdmin},
			issuedAt:    issuedAt,
			expiresAt:   expiresAt,
			serial:      serial,
			fingerprint: fp,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			cert, err := NewClientCertificate(
				tt.clientID, tt.sanURI, tt.roles,
				tt.issuedAt, tt.expiresAt,
				tt.serial, tt.fingerprint,
			)

			if tt.wantErr {
				if err == nil {
					t.Fatalf("NewClientCertificate() expected error containing %q, got nil", tt.errSubstr)
				}
				if !strings.Contains(err.Error(), tt.errSubstr) {
					t.Fatalf("NewClientCertificate() error = %q, want substring %q", err.Error(), tt.errSubstr)
				}
				return
			}

			if err != nil {
				t.Fatalf("NewClientCertificate() unexpected error: %v", err)
			}

			if cert.ClientID.String() != tt.clientID.String() {
				t.Errorf("ClientID = %q, want %q", cert.ClientID.String(), tt.clientID.String())
			}
			if cert.Serial != tt.serial {
				t.Errorf("Serial = %q, want %q", cert.Serial, tt.serial)
			}
			if len(cert.Roles) != len(tt.roles) {
				t.Errorf("Roles length = %d, want %d", len(cert.Roles), len(tt.roles))
			}
		})
	}
}

func TestClientCertificate_IsExpired(t *testing.T) {
	t.Parallel()

	clientID, sanURI, roles, _, _, serial, fp := validCertFields(t)

	t.Run("not expired", func(t *testing.T) {
		t.Parallel()

		now := time.Now()
		cert, err := NewClientCertificate(clientID, sanURI, roles, now, now.Add(24*time.Hour), serial, fp)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if cert.IsExpired() {
			t.Error("IsExpired() = true for future expiry, want false")
		}
	})

	t.Run("expired", func(t *testing.T) {
		t.Parallel()

		past := time.Now().Add(-48 * time.Hour)
		cert, err := NewClientCertificate(clientID, sanURI, roles, past, past.Add(24*time.Hour), serial, fp)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if !cert.IsExpired() {
			t.Error("IsExpired() = false for past expiry, want true")
		}
	})
}

func TestClientCertificate_HasRole(t *testing.T) {
	t.Parallel()

	clientID, sanURI, _, issuedAt, expiresAt, serial, fp := validCertFields(t)

	cert, err := NewClientCertificate(
		clientID, sanURI,
		[]identity.Role{identity.RoleOperator, identity.RoleViewer},
		issuedAt, expiresAt, serial, fp,
	)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if !cert.HasRole(identity.RoleOperator) {
		t.Error("HasRole(RoleOperator) = false, want true")
	}

	if !cert.HasRole(identity.RoleViewer) {
		t.Error("HasRole(RoleViewer) = false, want true")
	}

	if cert.HasRole(identity.RoleAdmin) {
		t.Error("HasRole(RoleAdmin) = true, want false")
	}
}
