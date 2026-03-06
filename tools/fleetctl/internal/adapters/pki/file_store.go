package pki

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain/identity"
)

const (
	pkiDir          = "pki"
	clientKeyFile   = "client.key"
	clientCertFile  = "client.crt"
	caCertFile      = "ca.crt"
	serverNameFile  = "server_name"
	dirPermission   = 0700
	filePermission  = 0600
)

// FileStore implements ports.CredentialStore by persisting mTLS material
// as PEM files under baseDir/pki/.
type FileStore struct {
	baseDir string // e.g. ~/.config/fleetctl/
}

// NewFileStore creates a FileStore rooted at the given base directory.
func NewFileStore(baseDir string) *FileStore {
	return &FileStore{baseDir: baseDir}
}

// pkiPath returns the full path to a file inside the pki sub-directory.
func (s *FileStore) pkiPath(name string) string {
	return filepath.Join(s.baseDir, pkiDir, name)
}

// Load reads the persisted credential material and returns a fully
// initialised Credentials value object. Returns an error if no
// credentials have been saved yet or the material is corrupt.
func (s *FileStore) Load() (identity.Credentials, error) {
	certPEM, err := os.ReadFile(s.pkiPath(clientCertFile))
	if err != nil {
		return identity.Credentials{}, fmt.Errorf("load client cert: %w", err)
	}

	keyPEM, err := os.ReadFile(s.pkiPath(clientKeyFile))
	if err != nil {
		return identity.Credentials{}, fmt.Errorf("load client key: %w", err)
	}

	caPEM, err := os.ReadFile(s.pkiPath(caCertFile))
	if err != nil {
		return identity.Credentials{}, fmt.Errorf("load ca cert: %w", err)
	}

	serverNameBytes, err := os.ReadFile(s.pkiPath(serverNameFile))
	if err != nil {
		return identity.Credentials{}, fmt.Errorf("load server name: %w", err)
	}
	serverName := string(serverNameBytes)

	creds, err := identity.NewCredentials(certPEM, keyPEM, caPEM, serverName)
	if err != nil {
		return identity.Credentials{}, fmt.Errorf("parse credentials: %w", err)
	}

	return creds, nil
}

// Save atomically persists the given PEM-encoded certificate, key,
// and CA chain alongside the server name so that Load can reconstruct
// Credentials later.
func (s *FileStore) Save(certPEM, keyPEM, caPEM []byte, serverName string) error {
	dir := filepath.Join(s.baseDir, pkiDir)
	if err := os.MkdirAll(dir, dirPermission); err != nil {
		return fmt.Errorf("create pki directory: %w", err)
	}

	files := []struct {
		name string
		data []byte
	}{
		{clientKeyFile, keyPEM},
		{clientCertFile, certPEM},
		{caCertFile, caPEM},
		{serverNameFile, []byte(serverName)},
	}

	for _, f := range files {
		path := filepath.Join(dir, f.name)
		if err := os.WriteFile(path, f.data, filePermission); err != nil {
			return fmt.Errorf("write %s: %w", f.name, err)
		}
	}

	return nil
}

// Exists returns true when credential material is present on disk.
// It does NOT validate the material; call Load for full validation.
func (s *FileStore) Exists() bool {
	_, err := os.Stat(s.pkiPath(clientCertFile))
	return err == nil
}
