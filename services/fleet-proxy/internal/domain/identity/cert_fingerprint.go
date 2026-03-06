package identity

import (
	"crypto/sha256"
	"encoding/hex"
)

// CertFingerprint is a value object wrapping a SHA-256 fingerprint of a
// DER-encoded certificate. It is always exactly 32 bytes.
type CertFingerprint struct {
	hash [32]byte
}

// NewCertFingerprint computes the SHA-256 fingerprint of the given
// DER-encoded certificate bytes.
func NewCertFingerprint(der []byte) CertFingerprint {
	return CertFingerprint{hash: sha256.Sum256(der)}
}

// String returns the hex-encoded fingerprint.
func (f CertFingerprint) String() string {
	return hex.EncodeToString(f.hash[:])
}

// Bytes returns the raw 32-byte SHA-256 hash.
func (f CertFingerprint) Bytes() [32]byte {
	return f.hash
}

// IsZero reports whether the fingerprint is the zero value (all zeroes).
func (f CertFingerprint) IsZero() bool {
	return f.hash == [32]byte{}
}
