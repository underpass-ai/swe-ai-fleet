package command

import (
	"context"
	"errors"
	"strings"
	"testing"
	"time"
)

func TestRenewHandler_Handle(t *testing.T) {
	t.Parallel()

	validCert := mustClientCertificate(t)
	validChain := []byte("-----BEGIN CERTIFICATE-----\nfake\n-----END CERTIFICATE-----\n")
	validClientID := "spiffe://swe-ai-fleet/user/tirso/device/macbook"

	tests := []struct {
		name      string
		cmd       RenewCmd
		issuer    *fakeCertificateIssuer
		wantErr   bool
		errSubstr string
		checkRes  func(t *testing.T, res RenewResult)
	}{
		{
			name: "successful renewal",
			cmd: RenewCmd{
				CSRPEM:   []byte("-----BEGIN CERTIFICATE REQUEST-----\nfake\n-----END CERTIFICATE REQUEST-----\n"),
				ClientID: validClientID,
			},
			issuer: &fakeCertificateIssuer{cert: validCert, chainPEM: validChain},
			checkRes: func(t *testing.T, res RenewResult) {
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
				// Verify ExpiresAt is valid RFC3339.
				if _, err := time.Parse(time.RFC3339, res.ExpiresAt); err != nil {
					t.Errorf("ExpiresAt %q is not valid RFC3339: %v", res.ExpiresAt, err)
				}
			},
		},
		{
			name: "empty CSR",
			cmd: RenewCmd{
				CSRPEM:   nil,
				ClientID: validClientID,
			},
			issuer:    &fakeCertificateIssuer{},
			wantErr:   true,
			errSubstr: "CSR PEM is required",
		},
		{
			name: "empty client ID",
			cmd: RenewCmd{
				CSRPEM:   []byte("csr-data"),
				ClientID: "",
			},
			issuer:    &fakeCertificateIssuer{},
			wantErr:   true,
			errSubstr: "client ID is required",
		},
		{
			name: "invalid client ID format",
			cmd: RenewCmd{
				CSRPEM:   []byte("csr-data"),
				ClientID: "not-a-spiffe-uri",
			},
			issuer:    &fakeCertificateIssuer{},
			wantErr:   true,
			errSubstr: "invalid client ID",
		},
		{
			name: "certificate issuer returns error",
			cmd: RenewCmd{
				CSRPEM:   []byte("bad-csr"),
				ClientID: validClientID,
			},
			issuer:    &fakeCertificateIssuer{err: errors.New("pki: no PEM block found")},
			wantErr:   true,
			errSubstr: "CSR signing failed",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			audit := &fakeAuditLogger{}
			handler := NewRenewHandler(tt.issuer, audit, 24*time.Hour)

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
			if audit.events[0].Method != "Renew" {
				t.Errorf("audit Method = %q, want %q", audit.events[0].Method, "Renew")
			}
			if audit.events[0].ClientID != validClientID {
				t.Errorf("audit ClientID = %q, want %q", audit.events[0].ClientID, validClientID)
			}

			if tt.checkRes != nil {
				tt.checkRes(t, res)
			}
		})
	}
}

func TestRenewCmd_Validate(t *testing.T) {
	t.Parallel()

	valid := RenewCmd{
		CSRPEM:   []byte("csr-data"),
		ClientID: "spiffe://swe-ai-fleet/user/tirso/device/macbook",
	}

	if err := valid.Validate(); err != nil {
		t.Errorf("valid command: Validate() = %v, want nil", err)
	}
}
