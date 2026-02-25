package command

import (
	"crypto/rand"
	"fmt"
)

// generateRequestID creates a random 16-byte hex string suitable for use
// as an idempotency key / request ID in control plane RPCs.
func generateRequestID() (string, error) {
	b := make([]byte, 16)
	if _, err := rand.Read(b); err != nil {
		return "", err
	}
	return fmt.Sprintf("%x", b), nil
}
