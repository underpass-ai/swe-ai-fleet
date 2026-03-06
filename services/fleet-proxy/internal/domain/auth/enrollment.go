package auth

import (
	"crypto/sha256"
	"errors"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/identity"
)

// EnrollmentRequest represents a client's request to enroll into the fleet
// by submitting a Certificate Signing Request (CSR). This is an entity
// identified by the combination of ApiKeyID and CSRHash.
type EnrollmentRequest struct {
	// CSR is the DER- or PEM-encoded Certificate Signing Request.
	CSR []byte

	// RequestedIdentity is the SAN URI the client wishes to be issued.
	RequestedIdentity identity.SANUri

	// ApiKeyID identifies the API key used to authenticate this enrollment.
	ApiKeyID identity.ApiKeyID

	// RequestedAt is the timestamp when the enrollment was requested.
	RequestedAt time.Time

	// CSRHash is the SHA-256 hash of the CSR, used for deduplication.
	CSRHash [32]byte
}

// NewEnrollmentRequest creates a validated EnrollmentRequest.
// It requires a non-empty CSR, a valid SAN URI, and a valid API key ID.
// The CSRHash is computed automatically from the CSR bytes.
// RequestedAt is set to the current time.
func NewEnrollmentRequest(
	csr []byte,
	requestedIdentity identity.SANUri,
	apiKeyID identity.ApiKeyID,
) (EnrollmentRequest, error) {
	if len(csr) == 0 {
		return EnrollmentRequest{}, errors.New("CSR cannot be empty")
	}

	if requestedIdentity.IsZero() {
		return EnrollmentRequest{}, errors.New("requested identity cannot be empty")
	}

	if apiKeyID.IsZero() {
		return EnrollmentRequest{}, errors.New("API key ID cannot be empty")
	}

	return EnrollmentRequest{
		CSR:               csr,
		RequestedIdentity: requestedIdentity,
		ApiKeyID:          apiKeyID,
		RequestedAt:       time.Now(),
		CSRHash:           sha256.Sum256(csr),
	}, nil
}
