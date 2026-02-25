package ports

import (
	"context"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/auth"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/identity"
)

// CertificateIssuer is a port for the internal PKI that signs certificate
// signing requests during the enrollment flow.
type CertificateIssuer interface {
	// SignCSR signs the provided CSR bytes, embedding the given SAN URI and
	// setting the certificate validity to ttl. It returns the signed
	// ClientCertificate metadata, the PEM-encoded certificate chain, and any
	// error encountered during signing.
	SignCSR(ctx context.Context, csr []byte, san identity.SANUri, ttl time.Duration) (auth.ClientCertificate, []byte, error)
}
