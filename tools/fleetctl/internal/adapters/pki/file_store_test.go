package pki

import (
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"math/big"
	"os"
	"path/filepath"
	"testing"
	"time"
)

// testPKIMaterial generates a self-signed CA and a leaf certificate+key suitable
// for the FileStore tests. Returns certPEM, keyPEM, caPEM.
func testPKIMaterial(t *testing.T) ([]byte, []byte, []byte) {
	t.Helper()

	caKey, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		t.Fatalf("generate CA key: %v", err)
	}
	caTemplate := &x509.Certificate{
		SerialNumber:          big.NewInt(1),
		Subject:               pkix.Name{Organization: []string{"Test CA"}},
		NotBefore:             time.Now().Add(-time.Hour),
		NotAfter:              time.Now().Add(24 * time.Hour),
		KeyUsage:              x509.KeyUsageCertSign | x509.KeyUsageCRLSign,
		BasicConstraintsValid: true,
		IsCA:                  true,
	}
	caDER, err := x509.CreateCertificate(rand.Reader, caTemplate, caTemplate, &caKey.PublicKey, caKey)
	if err != nil {
		t.Fatalf("create CA cert: %v", err)
	}
	caPEM := pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: caDER})

	leafKey, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		t.Fatalf("generate leaf key: %v", err)
	}
	leafTemplate := &x509.Certificate{
		SerialNumber: big.NewInt(2),
		Subject:      pkix.Name{Organization: []string{"Test Leaf"}},
		NotBefore:    time.Now().Add(-time.Hour),
		NotAfter:     time.Now().Add(24 * time.Hour),
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

func TestSave_Success(t *testing.T) {
	dir := t.TempDir()
	store := NewFileStore(dir)

	certPEM, keyPEM, caPEM := testPKIMaterial(t)
	err := store.Save(certPEM, keyPEM, caPEM, "fleet.example.com")
	if err != nil {
		t.Fatalf("Save() error: %v", err)
	}

	// Verify all four files exist.
	expected := []string{clientCertFile, clientKeyFile, caCertFile, serverNameFile}
	for _, name := range expected {
		path := filepath.Join(dir, pkiDir, name)
		if _, err := os.Stat(path); err != nil {
			t.Errorf("file %s not found after Save: %v", name, err)
		}
	}
}

func TestSave_InvalidPath(t *testing.T) {
	dir := t.TempDir()
	locked := filepath.Join(dir, "locked")
	if err := os.Mkdir(locked, 0500); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { os.Chmod(locked, 0700) })

	store := NewFileStore(filepath.Join(locked, "no-exist"))
	err := store.Save([]byte("c"), []byte("k"), []byte("ca"), "sn")
	if err == nil {
		t.Fatal("Save() expected error for unwritable path, got nil")
	}
}

func TestLoad_Success(t *testing.T) {
	dir := t.TempDir()
	store := NewFileStore(dir)

	certPEM, keyPEM, caPEM := testPKIMaterial(t)
	if err := store.Save(certPEM, keyPEM, caPEM, "fleet.test"); err != nil {
		t.Fatalf("Save() error: %v", err)
	}

	creds, err := store.Load()
	if err != nil {
		t.Fatalf("Load() error: %v", err)
	}
	if creds.ServerName() != "fleet.test" {
		t.Errorf("ServerName() = %q, want %q", creds.ServerName(), "fleet.test")
	}
}

func TestLoad_NotFound(t *testing.T) {
	dir := t.TempDir()
	store := NewFileStore(dir)

	_, err := store.Load()
	if err == nil {
		t.Fatal("Load() expected error when no credentials saved, got nil")
	}
}

func TestLoad_CorruptCert(t *testing.T) {
	dir := t.TempDir()
	store := NewFileStore(dir)

	certPEM, keyPEM, caPEM := testPKIMaterial(t)
	if err := store.Save(certPEM, keyPEM, caPEM, "fleet.test"); err != nil {
		t.Fatal(err)
	}

	// Corrupt the client cert file.
	certPath := filepath.Join(dir, pkiDir, clientCertFile)
	if err := os.WriteFile(certPath, []byte("not-a-cert"), 0600); err != nil {
		t.Fatal(err)
	}

	_, err := store.Load()
	if err == nil {
		t.Fatal("Load() expected error for corrupt cert, got nil")
	}
}

func TestLoad_MissingKey(t *testing.T) {
	dir := t.TempDir()
	store := NewFileStore(dir)

	certPEM, keyPEM, caPEM := testPKIMaterial(t)
	if err := store.Save(certPEM, keyPEM, caPEM, "fleet.test"); err != nil {
		t.Fatal(err)
	}

	// Remove the key file.
	keyPath := filepath.Join(dir, pkiDir, clientKeyFile)
	os.Remove(keyPath)

	_, err := store.Load()
	if err == nil {
		t.Fatal("Load() expected error for missing key, got nil")
	}
}

func TestLoad_MissingCA(t *testing.T) {
	dir := t.TempDir()
	store := NewFileStore(dir)

	certPEM, keyPEM, caPEM := testPKIMaterial(t)
	if err := store.Save(certPEM, keyPEM, caPEM, "fleet.test"); err != nil {
		t.Fatal(err)
	}

	// Remove the CA file.
	caPath := filepath.Join(dir, pkiDir, caCertFile)
	os.Remove(caPath)

	_, err := store.Load()
	if err == nil {
		t.Fatal("Load() expected error for missing CA, got nil")
	}
}

func TestLoad_MissingServerName(t *testing.T) {
	dir := t.TempDir()
	store := NewFileStore(dir)

	certPEM, keyPEM, caPEM := testPKIMaterial(t)
	if err := store.Save(certPEM, keyPEM, caPEM, "fleet.test"); err != nil {
		t.Fatal(err)
	}

	// Remove the server_name file.
	snPath := filepath.Join(dir, pkiDir, serverNameFile)
	os.Remove(snPath)

	_, err := store.Load()
	if err == nil {
		t.Fatal("Load() expected error for missing server_name, got nil")
	}
}

func TestExists_True(t *testing.T) {
	dir := t.TempDir()
	store := NewFileStore(dir)

	certPEM, keyPEM, caPEM := testPKIMaterial(t)
	if err := store.Save(certPEM, keyPEM, caPEM, "fleet.test"); err != nil {
		t.Fatal(err)
	}

	if !store.Exists() {
		t.Error("Exists() = false after Save, want true")
	}
}

func TestExists_False(t *testing.T) {
	dir := t.TempDir()
	store := NewFileStore(dir)

	if store.Exists() {
		t.Error("Exists() = true with no saved credentials, want false")
	}
}

func TestSave_ThenLoad_Roundtrip(t *testing.T) {
	dir := t.TempDir()
	store := NewFileStore(dir)

	certPEM, keyPEM, caPEM := testPKIMaterial(t)
	serverName := "fleet.roundtrip.test"

	if err := store.Save(certPEM, keyPEM, caPEM, serverName); err != nil {
		t.Fatalf("Save() error: %v", err)
	}

	creds, err := store.Load()
	if err != nil {
		t.Fatalf("Load() error: %v", err)
	}

	if creds.ServerName() != serverName {
		t.Errorf("ServerName() = %q, want %q", creds.ServerName(), serverName)
	}
	if creds.IsExpired() {
		t.Error("loaded credentials are expired")
	}
}
