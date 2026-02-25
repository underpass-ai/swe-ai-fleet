package command

import (
	"context"
	"errors"
	"strings"
	"testing"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/auth"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/identity"
)

// ---------------------------------------------------------------------------
// Hand-written fakes
// ---------------------------------------------------------------------------

type fakeApiKeyStore struct {
	clientID identity.ClientID
	err      error
}

func (f *fakeApiKeyStore) Validate(_ context.Context, _, _ string) (identity.ClientID, error) {
	return f.clientID, f.err
}

type fakeCertificateIssuer struct {
	cert     auth.ClientCertificate
	chainPEM []byte
	err      error
}

func (f *fakeCertificateIssuer) SignCSR(_ context.Context, _ []byte, _ identity.SANUri, _ time.Duration) (auth.ClientCertificate, []byte, error) {
	return f.cert, f.chainPEM, f.err
}

type fakeAuditLogger struct {
	events []ports.AuditEvent
}

func (f *fakeAuditLogger) Record(_ context.Context, evt ports.AuditEvent) {
	f.events = append(f.events, evt)
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

func mustClientID(t *testing.T, raw string) identity.ClientID {
	t.Helper()
	cid, err := identity.NewClientID(raw)
	if err != nil {
		t.Fatalf("mustClientID(%q): %v", raw, err)
	}
	return cid
}

func mustSANUri(t *testing.T, raw string) identity.SANUri {
	t.Helper()
	san, err := identity.NewSANUri(raw)
	if err != nil {
		t.Fatalf("mustSANUri(%q): %v", raw, err)
	}
	return san
}

func mustClientCertificate(t *testing.T) auth.ClientCertificate {
	t.Helper()
	cid := mustClientID(t, "spiffe://swe-ai-fleet/user/tirso/device/macbook")
	san := mustSANUri(t, "spiffe://swe-ai-fleet/user/tirso/device/macbook")
	now := time.Now()
	fp := identity.NewCertFingerprint([]byte("fake-der-bytes-for-test"))
	cert, err := auth.NewClientCertificate(
		cid,
		san,
		[]identity.Role{identity.RoleOperator},
		now,
		now.Add(24*time.Hour),
		"abc123serial",
		fp,
	)
	if err != nil {
		t.Fatalf("mustClientCertificate: %v", err)
	}
	return cert
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

func TestEnrollHandler_Handle(t *testing.T) {
	t.Parallel()

	validClientID := mustClientID(t, "spiffe://swe-ai-fleet/user/tirso/device/macbook")
	validCert := mustClientCertificate(t)
	validChain := []byte("-----BEGIN CERTIFICATE-----\nfake\n-----END CERTIFICATE-----\n")

	tests := []struct {
		name      string
		cmd       EnrollCmd
		keyStore  *fakeApiKeyStore
		issuer    *fakeCertificateIssuer
		wantErr   bool
		errSubstr string
		checkRes  func(t *testing.T, res EnrollResult)
	}{
		{
			name: "successful enrollment",
			cmd: EnrollCmd{
				APIKeyID:      "key-id-1",
				APIKeySecret:  "secret-1",
				CSRPEM:        []byte("-----BEGIN CERTIFICATE REQUEST-----\nfake\n-----END CERTIFICATE REQUEST-----\n"),
				DeviceID:      "macbook",
				ClientVersion: "v0.1.0",
			},
			keyStore: &fakeApiKeyStore{clientID: validClientID},
			issuer:   &fakeCertificateIssuer{cert: validCert, chainPEM: validChain},
			checkRes: func(t *testing.T, res EnrollResult) {
				t.Helper()
				if len(res.ClientCertPEM) == 0 {
					t.Error("ClientCertPEM is empty")
				}
				if len(res.CAChainPEM) == 0 {
					t.Error("CAChainPEM is empty")
				}
				if res.ExpiresAt == "" {
					t.Error("ExpiresAt is empty")
				}
				if res.ClientID != validClientID.String() {
					t.Errorf("ClientID = %q, want %q", res.ClientID, validClientID.String())
				}
			},
		},
		{
			name: "empty API key ID",
			cmd: EnrollCmd{
				APIKeyID:     "",
				APIKeySecret: "secret-1",
				CSRPEM:       []byte("csr-data"),
				DeviceID:     "macbook",
			},
			keyStore:  &fakeApiKeyStore{},
			issuer:    &fakeCertificateIssuer{},
			wantErr:   true,
			errSubstr: "API key ID is required",
		},
		{
			name: "empty API key secret",
			cmd: EnrollCmd{
				APIKeyID:     "key-id-1",
				APIKeySecret: "",
				CSRPEM:       []byte("csr-data"),
				DeviceID:     "macbook",
			},
			keyStore:  &fakeApiKeyStore{},
			issuer:    &fakeCertificateIssuer{},
			wantErr:   true,
			errSubstr: "API key secret is required",
		},
		{
			name: "empty CSR",
			cmd: EnrollCmd{
				APIKeyID:     "key-id-1",
				APIKeySecret: "secret-1",
				CSRPEM:       nil,
				DeviceID:     "macbook",
			},
			keyStore:  &fakeApiKeyStore{},
			issuer:    &fakeCertificateIssuer{},
			wantErr:   true,
			errSubstr: "CSR PEM is required",
		},
		{
			name: "empty device ID",
			cmd: EnrollCmd{
				APIKeyID:     "key-id-1",
				APIKeySecret: "secret-1",
				CSRPEM:       []byte("csr-data"),
				DeviceID:     "",
			},
			keyStore:  &fakeApiKeyStore{},
			issuer:    &fakeCertificateIssuer{},
			wantErr:   true,
			errSubstr: "device ID is required",
		},
		{
			name: "API key store returns error",
			cmd: EnrollCmd{
				APIKeyID:     "bad-key",
				APIKeySecret: "bad-secret",
				CSRPEM:       []byte("csr-data"),
				DeviceID:     "macbook",
			},
			keyStore:  &fakeApiKeyStore{err: errors.New("invalid API key")},
			issuer:    &fakeCertificateIssuer{},
			wantErr:   true,
			errSubstr: "API key validation failed",
		},
		{
			name: "certificate issuer returns error",
			cmd: EnrollCmd{
				APIKeyID:     "key-id-1",
				APIKeySecret: "secret-1",
				CSRPEM:       []byte("bad-csr"),
				DeviceID:     "macbook",
			},
			keyStore: &fakeApiKeyStore{clientID: validClientID},
			issuer:   &fakeCertificateIssuer{err: errors.New("pki: invalid CSR")},
			wantErr:  true,
			errSubstr: "CSR signing failed",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			audit := &fakeAuditLogger{}
			handler := NewEnrollHandler(tt.keyStore, tt.issuer, audit, 24*time.Hour)

			res, err := handler.Handle(context.Background(), tt.cmd)

			if tt.wantErr {
				if err == nil {
					t.Fatalf("Handle() expected error containing %q, got nil", tt.errSubstr)
				}
				if !strings.Contains(err.Error(), tt.errSubstr) {
					t.Fatalf("Handle() error = %q, want substring %q", err.Error(), tt.errSubstr)
				}
				// Verify audit was recorded on error.
				if len(audit.events) == 0 {
					t.Error("expected audit event on error, got none")
				}
				if len(audit.events) > 0 && audit.events[0].Success {
					t.Error("expected audit event Success=false on error")
				}
				return
			}

			if err != nil {
				t.Fatalf("Handle() unexpected error: %v", err)
			}

			// Verify audit was recorded on success.
			if len(audit.events) == 0 {
				t.Fatal("expected audit event on success, got none")
			}
			if !audit.events[0].Success {
				t.Error("expected audit event Success=true on success")
			}
			if audit.events[0].Method != "Enroll" {
				t.Errorf("audit Method = %q, want %q", audit.events[0].Method, "Enroll")
			}

			if tt.checkRes != nil {
				tt.checkRes(t, res)
			}
		})
	}
}

func TestEnrollCmd_Validate(t *testing.T) {
	t.Parallel()

	valid := EnrollCmd{
		APIKeyID:     "key-1",
		APIKeySecret: "secret-1",
		CSRPEM:       []byte("csr-data"),
		DeviceID:     "dev-1",
	}

	if err := valid.Validate(); err != nil {
		t.Errorf("valid command: Validate() = %v, want nil", err)
	}
}
