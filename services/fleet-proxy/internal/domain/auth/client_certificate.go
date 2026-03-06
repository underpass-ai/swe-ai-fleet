package auth

import (
	"errors"
	"slices"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/identity"
)

// ClientCertificate represents an issued mTLS client certificate within the fleet.
// It is an entity identified by its Serial number.
type ClientCertificate struct {
	// ClientID is the SPIFFE identity bound to this certificate.
	ClientID identity.ClientID

	// SANUri is the Subject Alternative Name URI embedded in the certificate.
	SANUri identity.SANUri

	// Roles are the authorization roles granted to the certificate holder.
	Roles []identity.Role

	// IssuedAt is the timestamp when the certificate was issued.
	IssuedAt time.Time

	// ExpiresAt is the timestamp when the certificate expires.
	ExpiresAt time.Time

	// Serial is the unique serial number of the certificate.
	Serial string

	// Fingerprint is the SHA-256 fingerprint of the DER-encoded certificate.
	Fingerprint identity.CertFingerprint
}

// NewClientCertificate creates a validated ClientCertificate.
func NewClientCertificate(
	clientID identity.ClientID,
	sanURI identity.SANUri,
	roles []identity.Role,
	issuedAt time.Time,
	expiresAt time.Time,
	serial string,
	fingerprint identity.CertFingerprint,
) (ClientCertificate, error) {
	if clientID.IsZero() {
		return ClientCertificate{}, errors.New("client ID cannot be empty")
	}

	if sanURI.IsZero() {
		return ClientCertificate{}, errors.New("SAN URI cannot be empty")
	}

	if len(roles) == 0 {
		return ClientCertificate{}, errors.New("at least one role is required")
	}

	for _, r := range roles {
		if !r.IsValid() {
			return ClientCertificate{}, errors.New("invalid role in certificate")
		}
	}

	if serial == "" {
		return ClientCertificate{}, errors.New("serial cannot be empty")
	}

	if fingerprint.IsZero() {
		return ClientCertificate{}, errors.New("fingerprint cannot be zero")
	}

	if !expiresAt.After(issuedAt) {
		return ClientCertificate{}, errors.New("expiresAt must be after issuedAt")
	}

	return ClientCertificate{
		ClientID:    clientID,
		SANUri:      sanURI,
		Roles:       roles,
		IssuedAt:    issuedAt,
		ExpiresAt:   expiresAt,
		Serial:      serial,
		Fingerprint: fingerprint,
	}, nil
}

// IsExpired reports whether the certificate has expired relative to the current time.
func (c ClientCertificate) IsExpired() bool {
	return time.Now().After(c.ExpiresAt)
}

// HasRole reports whether the certificate includes the given role.
func (c ClientCertificate) HasRole(role identity.Role) bool {
	return slices.Contains(c.Roles, role)
}
