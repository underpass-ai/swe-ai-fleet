package command

import (
	"context"
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"fmt"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
)

// RenewCmd carries the inputs for certificate renewal (currently empty —
// the existing mTLS identity is used automatically).
type RenewCmd struct{}

// RenewResult contains the outputs of a successful certificate renewal.
type RenewResult struct {
	ExpiresAt string
}

// RenewHandler orchestrates the certificate renewal ceremony: it generates a
// fresh ECDSA P-256 keypair, builds a CSR, calls the control plane Renew RPC,
// and persists the new credentials locally.
type RenewHandler struct {
	client    ports.FleetClient
	credStore ports.CredentialStore
	cfgStore  ports.ConfigStore
}

// NewRenewHandler creates a RenewHandler wired to the given ports.
func NewRenewHandler(client ports.FleetClient, credStore ports.CredentialStore, cfgStore ports.ConfigStore) *RenewHandler {
	return &RenewHandler{
		client:    client,
		credStore: credStore,
		cfgStore:  cfgStore,
	}
}

// Handle executes the renewal flow.
func (h *RenewHandler) Handle(ctx context.Context, _ RenewCmd) (RenewResult, error) {
	// 1. Load existing credentials to preserve the device CN.
	existingCreds, err := h.credStore.Load()
	if err != nil {
		return RenewResult{}, fmt.Errorf("renew: failed to load existing credentials: %w", err)
	}
	cn := existingCreds.CommonName()
	if cn == "" {
		cn = "fleetctl-device" // fallback
	}

	// 2. Generate ECDSA P-256 keypair.
	privKey, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		return RenewResult{}, fmt.Errorf("renew: failed to generate private key: %w", err)
	}

	// 3. Build a CSR using the original device CN.
	csrTemplate := &x509.CertificateRequest{
		Subject: pkix.Name{
			CommonName:   cn,
			Organization: []string{"swe-ai-fleet"},
		},
		SignatureAlgorithm: x509.ECDSAWithSHA256,
	}

	csrDER, err := x509.CreateCertificateRequest(rand.Reader, csrTemplate, privKey)
	if err != nil {
		return RenewResult{}, fmt.Errorf("renew: failed to create CSR: %w", err)
	}

	csrPEM := pem.EncodeToMemory(&pem.Block{
		Type:  "CERTIFICATE REQUEST",
		Bytes: csrDER,
	})

	// 4. Call the control plane.
	certPEM, caPEM, expiresAt, err := h.client.Renew(ctx, csrPEM)
	if err != nil {
		return RenewResult{}, fmt.Errorf("renew: server call failed: %w", err)
	}

	// 5. Encode the private key to PEM for storage.
	keyDER, err := x509.MarshalECPrivateKey(privKey)
	if err != nil {
		return RenewResult{}, fmt.Errorf("renew: failed to marshal private key: %w", err)
	}
	keyPEM := pem.EncodeToMemory(&pem.Block{
		Type:  "EC PRIVATE KEY",
		Bytes: keyDER,
	})

	// 6. Read server name from config.
	cfg, err := h.cfgStore.Load()
	if err != nil {
		return RenewResult{}, fmt.Errorf("renew: failed to load config: %w", err)
	}

	// 7. Persist credentials.
	if err := h.credStore.Save(certPEM, keyPEM, caPEM, cfg.ServerName); err != nil {
		return RenewResult{}, fmt.Errorf("renew: failed to save credentials: %w", err)
	}

	return RenewResult{
		ExpiresAt: expiresAt,
	}, nil
}
