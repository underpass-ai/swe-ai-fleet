package identity

import (
	"crypto/tls"
	"crypto/x509"
	"encoding/pem"
	"errors"
	"time"
)

// Credentials is a value object holding the mTLS identity of the enrolled device.
// It bundles the client certificate+key, the CA chain used to verify the server,
// and metadata such as expiration and expected server name.
type Credentials struct {
	privateKey tls.Certificate // contains both key + cert
	caChain    *x509.CertPool
	expiresAt  time.Time
	serverName string
}

// NewCredentials parses PEM-encoded certificate, key, and CA chain bytes and
// returns a fully initialised Credentials value. The serverName is used for
// TLS server-name override when connecting through a proxy / port-forward.
func NewCredentials(certPEM, keyPEM, caPEM []byte, serverName string) (Credentials, error) {
	if len(certPEM) == 0 {
		return Credentials{}, errors.New("credentials: certPEM is empty")
	}
	if len(keyPEM) == 0 {
		return Credentials{}, errors.New("credentials: keyPEM is empty")
	}
	if len(caPEM) == 0 {
		return Credentials{}, errors.New("credentials: caPEM is empty")
	}
	if serverName == "" {
		return Credentials{}, errors.New("credentials: serverName is empty")
	}

	cert, err := tls.X509KeyPair(certPEM, keyPEM)
	if err != nil {
		return Credentials{}, errors.New("credentials: failed to parse certificate/key pair: " + err.Error())
	}

	// Parse the leaf so we can read NotAfter.
	if cert.Leaf == nil {
		block, _ := pem.Decode(certPEM)
		if block == nil {
			return Credentials{}, errors.New("credentials: failed to decode certPEM block")
		}
		leaf, err := x509.ParseCertificate(block.Bytes)
		if err != nil {
			return Credentials{}, errors.New("credentials: failed to parse leaf certificate: " + err.Error())
		}
		cert.Leaf = leaf
	}

	caPool := x509.NewCertPool()
	if !caPool.AppendCertsFromPEM(caPEM) {
		return Credentials{}, errors.New("credentials: failed to append CA certificates")
	}

	return Credentials{
		privateKey: cert,
		caChain:    caPool,
		expiresAt:  cert.Leaf.NotAfter,
		serverName: serverName,
	}, nil
}

// TLSConfig returns a *tls.Config suitable for establishing an mTLS
// connection. The ServerName is set so that connections routed through
// kubectl port-forward (localhost) still verify correctly.
func (c Credentials) TLSConfig() *tls.Config {
	return &tls.Config{
		Certificates: []tls.Certificate{c.privateKey},
		RootCAs:      c.caChain,
		ServerName:   c.serverName,
		MinVersion:   tls.VersionTLS13,
	}
}

// ExpiresAt returns the time at which the client certificate expires.
func (c Credentials) ExpiresAt() time.Time {
	return c.expiresAt
}

// IsExpired returns true when the client certificate has passed its NotAfter.
func (c Credentials) IsExpired() bool {
	return time.Now().After(c.expiresAt)
}

// ServerName returns the TLS server name override.
func (c Credentials) ServerName() string {
	return c.serverName
}
