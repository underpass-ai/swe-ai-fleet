// Package pki provides the internal certificate authority adapter implementing
// ports.CertificateIssuer. It signs CSRs using a local CA key pair.
package pki

import (
	"context"
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"fmt"
	"math/big"
	"net/url"
	"os"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/auth"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/identity"
)

// maxSerialBits is the bit length used for generating random certificate serial numbers.
const maxSerialBits = 128

// Issuer is the internal PKI adapter. It holds a CA certificate and private
// key that are used to sign incoming CSRs.
type Issuer struct {
	caCert *x509.Certificate
	caKey  *ecdsa.PrivateKey
}

// NewIssuer loads the CA certificate and ECDSA private key from PEM files.
func NewIssuer(caCertPath, caKeyPath string) (*Issuer, error) {
	certPEM, err := os.ReadFile(caCertPath)
	if err != nil {
		return nil, fmt.Errorf("pki: read CA cert: %w", err)
	}

	block, _ := pem.Decode(certPEM)
	if block == nil {
		return nil, fmt.Errorf("pki: no PEM block found in CA cert file")
	}

	caCert, err := x509.ParseCertificate(block.Bytes)
	if err != nil {
		return nil, fmt.Errorf("pki: parse CA cert: %w", err)
	}

	keyPEM, err := os.ReadFile(caKeyPath)
	if err != nil {
		return nil, fmt.Errorf("pki: read CA key: %w", err)
	}

	keyBlock, _ := pem.Decode(keyPEM)
	if keyBlock == nil {
		return nil, fmt.Errorf("pki: no PEM block found in CA key file")
	}

	caKey, err := x509.ParseECPrivateKey(keyBlock.Bytes)
	if err != nil {
		return nil, fmt.Errorf("pki: parse CA key: %w", err)
	}

	return &Issuer{
		caCert: caCert,
		caKey:  caKey,
	}, nil
}

// NewIssuerFromKeyPair creates an Issuer directly from an in-memory CA
// certificate and key. This is useful for testing.
func NewIssuerFromKeyPair(caCert *x509.Certificate, caKey *ecdsa.PrivateKey) *Issuer {
	return &Issuer{
		caCert: caCert,
		caKey:  caKey,
	}
}

// SignCSR signs the provided PEM-encoded CSR, embedding the given SAN URI and
// setting the certificate validity to ttl. It returns the signed
// ClientCertificate metadata, the PEM-encoded certificate chain (leaf + CA),
// and any error encountered during signing.
func (i *Issuer) SignCSR(_ context.Context, csrPEM []byte, san identity.SANUri, ttl time.Duration) (auth.ClientCertificate, []byte, error) {
	// Parse the CSR from PEM.
	block, _ := pem.Decode(csrPEM)
	if block == nil {
		return auth.ClientCertificate{}, nil, fmt.Errorf("pki: no PEM block found in CSR")
	}

	csr, err := x509.ParseCertificateRequest(block.Bytes)
	if err != nil {
		return auth.ClientCertificate{}, nil, fmt.Errorf("pki: parse CSR: %w", err)
	}

	if err := csr.CheckSignature(); err != nil {
		return auth.ClientCertificate{}, nil, fmt.Errorf("pki: invalid CSR signature: %w", err)
	}

	// Generate a random serial number.
	serialLimit := new(big.Int).Lsh(big.NewInt(1), maxSerialBits)
	serial, err := rand.Int(rand.Reader, serialLimit)
	if err != nil {
		return auth.ClientCertificate{}, nil, fmt.Errorf("pki: generate serial: %w", err)
	}

	// Parse the SAN URI for embedding into the certificate.
	sanURL, err := url.Parse(san.String())
	if err != nil {
		return auth.ClientCertificate{}, nil, fmt.Errorf("pki: parse SAN URI: %w", err)
	}

	now := time.Now()
	notAfter := now.Add(ttl)

	// Build the leaf certificate template.
	template := &x509.Certificate{
		SerialNumber: serial,
		Subject: pkix.Name{
			CommonName:   san.String(),
			Organization: []string{"swe-ai-fleet"},
		},
		NotBefore:             now,
		NotAfter:              notAfter,
		KeyUsage:              x509.KeyUsageDigitalSignature | x509.KeyUsageKeyEncipherment,
		ExtKeyUsage:           []x509.ExtKeyUsage{x509.ExtKeyUsageClientAuth},
		URIs:                  []*url.URL{sanURL},
		BasicConstraintsValid: true,
	}

	// Sign the certificate with the CA.
	certDER, err := x509.CreateCertificate(rand.Reader, template, i.caCert, csr.PublicKey, i.caKey)
	if err != nil {
		return auth.ClientCertificate{}, nil, fmt.Errorf("pki: sign certificate: %w", err)
	}

	// Encode the leaf certificate to PEM.
	leafPEM := pem.EncodeToMemory(&pem.Block{
		Type:  "CERTIFICATE",
		Bytes: certDER,
	})

	// Encode the CA certificate to PEM for the chain.
	caPEM := pem.EncodeToMemory(&pem.Block{
		Type:  "CERTIFICATE",
		Bytes: i.caCert.Raw,
	})

	// Build the full chain: leaf + CA.
	chainPEM := append(leafPEM, caPEM...)

	// Construct the ClientID from the SAN URI. The SAN URI follows the
	// SPIFFE format: spiffe://swe-ai-fleet/user/{userId}/device/{deviceId}.
	clientID, err := identity.NewClientID(san.String())
	if err != nil {
		return auth.ClientCertificate{}, nil, fmt.Errorf("pki: derive client ID from SAN: %w", err)
	}

	fingerprint := identity.NewCertFingerprint(certDER)

	cert, err := auth.NewClientCertificate(
		clientID,
		san,
		[]identity.Role{identity.RoleOperator}, // default role for newly enrolled clients
		now,
		notAfter,
		serial.Text(16),
		fingerprint,
	)
	if err != nil {
		return auth.ClientCertificate{}, nil, fmt.Errorf("pki: build client certificate: %w", err)
	}

	return cert, chainPEM, nil
}

// GenerateSelfSignedCA creates a self-signed CA certificate and ECDSA key pair.
// This is intended for development and testing only.
func GenerateSelfSignedCA() (*x509.Certificate, *ecdsa.PrivateKey, error) {
	key, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		return nil, nil, fmt.Errorf("pki: generate CA key: %w", err)
	}

	serialLimit := new(big.Int).Lsh(big.NewInt(1), maxSerialBits)
	serial, err := rand.Int(rand.Reader, serialLimit)
	if err != nil {
		return nil, nil, fmt.Errorf("pki: generate CA serial: %w", err)
	}

	template := &x509.Certificate{
		SerialNumber: serial,
		Subject: pkix.Name{
			CommonName:   "swe-ai-fleet CA",
			Organization: []string{"swe-ai-fleet"},
		},
		NotBefore:             time.Now(),
		NotAfter:              time.Now().Add(10 * 365 * 24 * time.Hour),
		KeyUsage:              x509.KeyUsageCertSign | x509.KeyUsageCRLSign,
		BasicConstraintsValid: true,
		IsCA:                  true,
		MaxPathLen:            1,
	}

	certDER, err := x509.CreateCertificate(rand.Reader, template, template, &key.PublicKey, key)
	if err != nil {
		return nil, nil, fmt.Errorf("pki: create CA certificate: %w", err)
	}

	cert, err := x509.ParseCertificate(certDER)
	if err != nil {
		return nil, nil, fmt.Errorf("pki: parse CA certificate: %w", err)
	}

	return cert, key, nil
}
