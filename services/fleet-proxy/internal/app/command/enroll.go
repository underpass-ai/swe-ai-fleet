package command

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/identity"
)

// EnrollCmd carries the parameters for enrolling a new client into the fleet.
type EnrollCmd struct {
	// APIKeyID is the identifier of the API key used for authentication.
	APIKeyID string
	// APIKeySecret is the secret portion of the API key credential.
	APIKeySecret string
	// CSRPEM is the PEM-encoded Certificate Signing Request.
	CSRPEM []byte
	// DeviceID is the human-readable identifier for the enrolling device.
	DeviceID string
	// ClientVersion is the version string of the client software.
	ClientVersion string
}

// Validate checks that all required fields are present.
func (c EnrollCmd) Validate() error {
	if c.APIKeyID == "" {
		return errors.New("API key ID is required")
	}
	if c.APIKeySecret == "" {
		return errors.New("API key secret is required")
	}
	if len(c.CSRPEM) == 0 {
		return errors.New("CSR PEM is required")
	}
	if c.DeviceID == "" {
		return errors.New("device ID is required")
	}
	return nil
}

// EnrollResult holds the output of a successful enrollment.
type EnrollResult struct {
	// ClientCertPEM is the PEM-encoded signed client certificate chain.
	ClientCertPEM []byte
	// CAChainPEM is the PEM-encoded CA certificate chain for trust verification.
	CAChainPEM []byte
	// ExpiresAt is the certificate expiry time in RFC 3339 format.
	ExpiresAt string
	// ClientID is the SPIFFE URI assigned to the enrolled client.
	ClientID string
}

// EnrollHandler orchestrates client enrollment by validating the API key,
// signing the CSR, and recording an audit event.
type EnrollHandler struct {
	keyStore ports.ApiKeyStore
	issuer   ports.CertificateIssuer
	audit    ports.AuditLogger
	certTTL  time.Duration
}

// NewEnrollHandler wires the handler to its ports.
func NewEnrollHandler(
	ks ports.ApiKeyStore,
	issuer ports.CertificateIssuer,
	audit ports.AuditLogger,
	certTTL time.Duration,
) *EnrollHandler {
	return &EnrollHandler{
		keyStore: ks,
		issuer:   issuer,
		audit:    audit,
		certTTL:  certTTL,
	}
}

// Handle validates the enrollment command, authenticates the API key, signs the
// CSR, records an audit event, and returns the enrollment result.
func (h *EnrollHandler) Handle(ctx context.Context, cmd EnrollCmd) (EnrollResult, error) {
	if err := cmd.Validate(); err != nil {
		h.recordAudit(ctx, "", cmd.DeviceID, false, err.Error())
		return EnrollResult{}, err
	}

	// Authenticate the API key and retrieve the associated ClientID.
	clientID, err := h.keyStore.Validate(ctx, cmd.APIKeyID, cmd.APIKeySecret)
	if err != nil {
		h.recordAudit(ctx, "", cmd.DeviceID, false, fmt.Sprintf("API key validation failed: %v", err))
		return EnrollResult{}, fmt.Errorf("API key validation failed: %w", err)
	}

	// Build the SAN URI from the authenticated client identity.
	san, err := identity.NewSANUri(clientID.String())
	if err != nil {
		h.recordAudit(ctx, clientID.String(), cmd.DeviceID, false, fmt.Sprintf("invalid SAN URI: %v", err))
		return EnrollResult{}, fmt.Errorf("invalid SAN URI from client ID: %w", err)
	}

	// Sign the CSR using the internal PKI.
	cert, chainPEM, err := h.issuer.SignCSR(ctx, cmd.CSRPEM, san, h.certTTL)
	if err != nil {
		h.recordAudit(ctx, clientID.String(), cmd.DeviceID, false, fmt.Sprintf("CSR signing failed: %v", err))
		return EnrollResult{}, fmt.Errorf("CSR signing failed: %w", err)
	}

	h.recordAudit(ctx, clientID.String(), cmd.DeviceID, true, "")

	return EnrollResult{
		ClientCertPEM: chainPEM,
		CAChainPEM:    chainPEM,
		ExpiresAt:     cert.ExpiresAt.Format(time.RFC3339),
		ClientID:      clientID.String(),
	}, nil
}

func (h *EnrollHandler) recordAudit(ctx context.Context, clientID, deviceID string, success bool, errMsg string) {
	reqID := deviceID
	if clientID != "" {
		reqID = clientID + "/" + deviceID
	}
	h.audit.Record(ctx, ports.AuditEvent{
		ClientID:  clientID,
		Method:    "Enroll",
		RequestID: reqID,
		Timestamp: time.Now(),
		Success:   success,
		Error:     errMsg,
	})
}
