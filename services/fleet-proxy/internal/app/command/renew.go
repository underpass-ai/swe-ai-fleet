package command

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/identity"
)

// RenewCmd carries the parameters for renewing an existing client certificate.
// The ClientID comes from the mTLS context (already authenticated).
type RenewCmd struct {
	// CSRPEM is the PEM-encoded Certificate Signing Request for the new certificate.
	CSRPEM []byte
	// ClientID is the SPIFFE URI of the already-authenticated client (from mTLS).
	ClientID string
}

// Validate checks that all required fields are present.
func (c RenewCmd) Validate() error {
	if len(c.CSRPEM) == 0 {
		return errors.New("CSR PEM is required")
	}
	if c.ClientID == "" {
		return errors.New("client ID is required")
	}
	return nil
}

// RenewResult holds the output of a successful certificate renewal.
type RenewResult struct {
	// ClientCertPEM is the PEM-encoded signed client certificate chain.
	ClientCertPEM []byte
	// CAChainPEM is the PEM-encoded CA certificate chain for trust verification.
	CAChainPEM []byte
	// ExpiresAt is the certificate expiry time in RFC 3339 format.
	ExpiresAt string
}

// RenewHandler orchestrates certificate renewal for already-authenticated clients.
type RenewHandler struct {
	issuer  ports.CertificateIssuer
	audit   ports.AuditLogger
	certTTL time.Duration
}

// NewRenewHandler wires the handler to its ports.
func NewRenewHandler(
	issuer ports.CertificateIssuer,
	audit ports.AuditLogger,
	certTTL time.Duration,
) *RenewHandler {
	return &RenewHandler{
		issuer:  issuer,
		audit:   audit,
		certTTL: certTTL,
	}
}

// Handle validates the renewal command, builds the SAN URI from the
// authenticated client ID, signs the new CSR, and records an audit event.
func (h *RenewHandler) Handle(ctx context.Context, cmd RenewCmd) (RenewResult, error) {
	if err := cmd.Validate(); err != nil {
		h.recordAudit(ctx, cmd.ClientID, false, err.Error())
		return RenewResult{}, err
	}

	// Parse and validate the client ID as a domain value object.
	clientID, err := identity.NewClientID(cmd.ClientID)
	if err != nil {
		h.recordAudit(ctx, cmd.ClientID, false, fmt.Sprintf("invalid client ID: %v", err))
		return RenewResult{}, fmt.Errorf("invalid client ID: %w", err)
	}

	// Build the SAN URI from the authenticated client identity.
	san, err := identity.NewSANUri(clientID.String())
	if err != nil {
		h.recordAudit(ctx, cmd.ClientID, false, fmt.Sprintf("invalid SAN URI: %v", err))
		return RenewResult{}, fmt.Errorf("invalid SAN URI from client ID: %w", err)
	}

	// Sign the CSR using the internal PKI.
	cert, chainPEM, err := h.issuer.SignCSR(ctx, cmd.CSRPEM, san, h.certTTL)
	if err != nil {
		h.recordAudit(ctx, cmd.ClientID, false, fmt.Sprintf("CSR signing failed: %v", err))
		return RenewResult{}, fmt.Errorf("CSR signing failed: %w", err)
	}

	h.recordAudit(ctx, cmd.ClientID, true, "")

	return RenewResult{
		ClientCertPEM: chainPEM,
		CAChainPEM:    chainPEM,
		ExpiresAt:     cert.ExpiresAt.Format(time.RFC3339),
	}, nil
}

func (h *RenewHandler) recordAudit(ctx context.Context, clientID string, success bool, errMsg string) {
	h.audit.Record(ctx, ports.AuditEvent{
		ClientID:  clientID,
		Method:    "Renew",
		RequestID: clientID,
		Timestamp: time.Now(),
		Success:   success,
		Error:     errMsg,
	})
}
