package command

import (
	"context"
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"errors"
	"fmt"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
)

// EnrollCmd carries the inputs required to enroll this device with the
// fleet control plane.
type EnrollCmd struct {
	APIKey   string
	DeviceID string
}

// EnrollResult contains the outputs of a successful enrollment.
type EnrollResult struct {
	ClientID  string
	ExpiresAt string
}

// EnrollHandler orchestrates the enrollment ceremony: it generates a fresh
// ECDSA P-256 keypair, builds a CSR, calls the control plane Enroll RPC,
// and persists the returned credentials locally.
type EnrollHandler struct {
	client    ports.FleetClient
	credStore ports.CredentialStore
	cfgStore  ports.ConfigStore
}

// NewEnrollHandler creates an EnrollHandler wired to the given ports.
func NewEnrollHandler(client ports.FleetClient, credStore ports.CredentialStore, cfgStore ports.ConfigStore) *EnrollHandler {
	return &EnrollHandler{
		client:    client,
		credStore: credStore,
		cfgStore:  cfgStore,
	}
}

// Handle executes the enrollment flow. It is idempotent in the sense that
// calling it again overwrites any previously stored credentials.
func (h *EnrollHandler) Handle(ctx context.Context, cmd EnrollCmd) (EnrollResult, error) {
	if cmd.APIKey == "" {
		return EnrollResult{}, errors.New("enroll: api key is required")
	}
	if cmd.DeviceID == "" {
		return EnrollResult{}, errors.New("enroll: device id is required")
	}

	// 1. Generate ECDSA P-256 keypair.
	privKey, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		return EnrollResult{}, fmt.Errorf("enroll: failed to generate private key: %w", err)
	}

	// 2. Build a CSR with the device ID as the common name.
	csrTemplate := &x509.CertificateRequest{
		Subject: pkix.Name{
			CommonName:   cmd.DeviceID,
			Organization: []string{"swe-ai-fleet"},
		},
		SignatureAlgorithm: x509.ECDSAWithSHA256,
	}

	csrDER, err := x509.CreateCertificateRequest(rand.Reader, csrTemplate, privKey)
	if err != nil {
		return EnrollResult{}, fmt.Errorf("enroll: failed to create CSR: %w", err)
	}

	csrPEM := pem.EncodeToMemory(&pem.Block{
		Type:  "CERTIFICATE REQUEST",
		Bytes: csrDER,
	})

	// 3. Call the control plane.
	certPEM, caPEM, clientID, expiresAt, err := h.client.Enroll(ctx, cmd.APIKey, cmd.DeviceID, csrPEM)
	if err != nil {
		return EnrollResult{}, fmt.Errorf("enroll: server call failed: %w", err)
	}

	// 4. Encode the private key to PEM for storage.
	keyDER, err := x509.MarshalECPrivateKey(privKey)
	if err != nil {
		return EnrollResult{}, fmt.Errorf("enroll: failed to marshal private key: %w", err)
	}
	keyPEM := pem.EncodeToMemory(&pem.Block{
		Type:  "EC PRIVATE KEY",
		Bytes: keyDER,
	})

	// 5. Read server name from config (needed for credential storage).
	cfg, err := h.cfgStore.Load()
	if err != nil {
		return EnrollResult{}, fmt.Errorf("enroll: failed to load config: %w", err)
	}

	// 6. Persist credentials.
	if err := h.credStore.Save(certPEM, keyPEM, caPEM, cfg.ServerName); err != nil {
		return EnrollResult{}, fmt.Errorf("enroll: failed to save credentials: %w", err)
	}

	return EnrollResult{
		ClientID:  clientID,
		ExpiresAt: expiresAt,
	}, nil
}
