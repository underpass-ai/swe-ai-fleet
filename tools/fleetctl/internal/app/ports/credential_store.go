package ports

import (
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain/identity"
)

// CredentialStore persists and retrieves mTLS credentials on the local
// filesystem. Implementations handle PEM encoding/decoding, file
// permissions, and atomic writes.
type CredentialStore interface {
	// Load reads the persisted credential material and returns a fully
	// initialised Credentials value object. Returns an error if no
	// credentials have been saved yet or the material is corrupt.
	Load() (identity.Credentials, error)

	// Save atomically persists the given PEM-encoded certificate, key,
	// and CA chain alongside the server name so that Load can
	// reconstruct Credentials later.
	Save(certPEM, keyPEM, caPEM []byte, serverName string) error

	// Exists returns true when credential material is present on disk.
	// It does NOT validate the material; call Load for full validation.
	Exists() bool
}
