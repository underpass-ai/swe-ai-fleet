package identity

import (
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"math/big"
	"testing"
	"time"
)

// testPKI generates a self-signed CA and a leaf certificate+key for testing.
// Returns certPEM, keyPEM, caPEM.
func testPKI(t *testing.T, notAfter time.Time) ([]byte, []byte, []byte) {
	t.Helper()

	// --- CA ---
	caKey, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		t.Fatalf("generate CA key: %v", err)
	}
	caTemplate := &x509.Certificate{
		SerialNumber:          big.NewInt(1),
		Subject:               pkix.Name{Organization: []string{"Test CA"}},
		NotBefore:             time.Now().Add(-time.Hour),
		NotAfter:              notAfter.Add(time.Hour), // CA outlives leaf
		KeyUsage:              x509.KeyUsageCertSign | x509.KeyUsageCRLSign,
		BasicConstraintsValid: true,
		IsCA:                  true,
	}
	caDER, err := x509.CreateCertificate(rand.Reader, caTemplate, caTemplate, &caKey.PublicKey, caKey)
	if err != nil {
		t.Fatalf("create CA cert: %v", err)
	}
	caPEM := pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: caDER})

	// --- Leaf ---
	leafKey, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		t.Fatalf("generate leaf key: %v", err)
	}
	leafTemplate := &x509.Certificate{
		SerialNumber: big.NewInt(2),
		Subject:      pkix.Name{Organization: []string{"Test Leaf"}},
		NotBefore:    time.Now().Add(-time.Hour),
		NotAfter:     notAfter,
		KeyUsage:     x509.KeyUsageDigitalSignature,
		ExtKeyUsage:  []x509.ExtKeyUsage{x509.ExtKeyUsageClientAuth},
	}
	caCert, _ := x509.ParseCertificate(caDER)
	leafDER, err := x509.CreateCertificate(rand.Reader, leafTemplate, caCert, &leafKey.PublicKey, caKey)
	if err != nil {
		t.Fatalf("create leaf cert: %v", err)
	}
	certPEM := pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: leafDER})

	keyBytes, err := x509.MarshalECPrivateKey(leafKey)
	if err != nil {
		t.Fatalf("marshal leaf key: %v", err)
	}
	keyPEM := pem.EncodeToMemory(&pem.Block{Type: "EC PRIVATE KEY", Bytes: keyBytes})

	return certPEM, keyPEM, caPEM
}

func TestNewCredentials_Success(t *testing.T) {
	certPEM, keyPEM, caPEM := testPKI(t, time.Now().Add(24*time.Hour))

	creds, err := NewCredentials(certPEM, keyPEM, caPEM, "fleet.example.com")
	if err != nil {
		t.Fatalf("NewCredentials() error: %v", err)
	}
	if creds.ServerName() != "fleet.example.com" {
		t.Errorf("ServerName() = %q, want %q", creds.ServerName(), "fleet.example.com")
	}
	if creds.ExpiresAt().IsZero() {
		t.Error("ExpiresAt() is zero")
	}
	if creds.IsExpired() {
		t.Error("IsExpired() = true for freshly issued cert")
	}
}

func TestNewCredentials_EmptyCertPEM(t *testing.T) {
	_, keyPEM, caPEM := testPKI(t, time.Now().Add(time.Hour))
	_, err := NewCredentials(nil, keyPEM, caPEM, "server")
	if err == nil {
		t.Fatal("expected error for empty certPEM, got nil")
	}
}

func TestNewCredentials_EmptyKeyPEM(t *testing.T) {
	certPEM, _, caPEM := testPKI(t, time.Now().Add(time.Hour))
	_, err := NewCredentials(certPEM, nil, caPEM, "server")
	if err == nil {
		t.Fatal("expected error for empty keyPEM, got nil")
	}
}

func TestNewCredentials_EmptyCAPEM(t *testing.T) {
	certPEM, keyPEM, _ := testPKI(t, time.Now().Add(time.Hour))
	_, err := NewCredentials(certPEM, keyPEM, nil, "server")
	if err == nil {
		t.Fatal("expected error for empty caPEM, got nil")
	}
}

func TestNewCredentials_EmptyServerName(t *testing.T) {
	certPEM, keyPEM, caPEM := testPKI(t, time.Now().Add(time.Hour))
	_, err := NewCredentials(certPEM, keyPEM, caPEM, "")
	if err == nil {
		t.Fatal("expected error for empty serverName, got nil")
	}
}

func TestNewCredentials_InvalidKeyPair(t *testing.T) {
	certPEM, _, caPEM := testPKI(t, time.Now().Add(time.Hour))
	// Generate a different key that does not match the cert.
	_, otherKeyPEM, _ := testPKI(t, time.Now().Add(time.Hour))

	_, err := NewCredentials(certPEM, otherKeyPEM, caPEM, "server")
	if err == nil {
		t.Fatal("expected error for mismatched cert/key pair, got nil")
	}
}

func TestNewCredentials_InvalidCAPEM(t *testing.T) {
	certPEM, keyPEM, _ := testPKI(t, time.Now().Add(time.Hour))
	badCA := []byte("not a valid PEM")

	_, err := NewCredentials(certPEM, keyPEM, badCA, "server")
	if err == nil {
		t.Fatal("expected error for invalid CA PEM, got nil")
	}
}

func TestCredentials_TLSConfig(t *testing.T) {
	certPEM, keyPEM, caPEM := testPKI(t, time.Now().Add(24*time.Hour))
	creds, err := NewCredentials(certPEM, keyPEM, caPEM, "fleet.test")
	if err != nil {
		t.Fatalf("NewCredentials() error: %v", err)
	}

	tlsCfg := creds.TLSConfig()
	if tlsCfg == nil {
		t.Fatal("TLSConfig() returned nil")
	}
	if tlsCfg.ServerName != "fleet.test" {
		t.Errorf("ServerName = %q, want %q", tlsCfg.ServerName, "fleet.test")
	}
	if tlsCfg.MinVersion != tls.VersionTLS13 {
		t.Errorf("MinVersion = %d, want %d", tlsCfg.MinVersion, tls.VersionTLS13)
	}
	if len(tlsCfg.Certificates) != 1 {
		t.Errorf("Certificates len = %d, want 1", len(tlsCfg.Certificates))
	}
	if tlsCfg.RootCAs == nil {
		t.Error("RootCAs is nil")
	}
}

func TestCredentials_IsExpired_True(t *testing.T) {
	// Create a cert that expired in the past.
	certPEM, keyPEM, caPEM := testPKI(t, time.Now().Add(-time.Minute))
	creds, err := NewCredentials(certPEM, keyPEM, caPEM, "server")
	if err != nil {
		t.Fatalf("NewCredentials() error: %v", err)
	}
	if !creds.IsExpired() {
		t.Error("IsExpired() = false for expired cert")
	}
}

func TestCredentials_ExpiresAt(t *testing.T) {
	target := time.Now().Add(48 * time.Hour)
	certPEM, keyPEM, caPEM := testPKI(t, target)
	creds, err := NewCredentials(certPEM, keyPEM, caPEM, "server")
	if err != nil {
		t.Fatalf("NewCredentials() error: %v", err)
	}

	// ExpiresAt should be close to the target (within a second, due to ASN.1 truncation).
	diff := creds.ExpiresAt().Sub(target)
	if diff < -time.Second || diff > time.Second {
		t.Errorf("ExpiresAt() diff from target = %v, want < 1s", diff)
	}
}
