package config

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

func TestNewFileConfig(t *testing.T) {
	fc := NewFileConfig("/some/dir")
	if fc.path != "/some/dir/config.yaml" {
		t.Errorf("path = %q, want %q", fc.path, "/some/dir/config.yaml")
	}
}

func TestLoad_NotFound_ReturnsZeroConfig(t *testing.T) {
	dir := t.TempDir()
	fc := NewFileConfig(dir)

	cfg, err := fc.Load()
	if err != nil {
		t.Fatalf("Load() unexpected error: %v", err)
	}
	if cfg.ServerName != "" || cfg.ProxyAddress != "" || cfg.DefaultProject != "" {
		t.Errorf("Load() on missing file should return zero Config, got %+v", cfg)
	}
}

func TestLoad_ValidYAML(t *testing.T) {
	dir := t.TempDir()
	content := []byte("server_name: fleet.example.com\nproxy_address: localhost:8443\ndefault_project: proj-1\n")
	if err := os.WriteFile(filepath.Join(dir, configFileName), content, 0600); err != nil {
		t.Fatal(err)
	}

	fc := NewFileConfig(dir)
	cfg, err := fc.Load()
	if err != nil {
		t.Fatalf("Load() error: %v", err)
	}
	if cfg.ServerName != "fleet.example.com" {
		t.Errorf("ServerName = %q, want %q", cfg.ServerName, "fleet.example.com")
	}
	if cfg.ProxyAddress != "localhost:8443" {
		t.Errorf("ProxyAddress = %q, want %q", cfg.ProxyAddress, "localhost:8443")
	}
	if cfg.DefaultProject != "proj-1" {
		t.Errorf("DefaultProject = %q, want %q", cfg.DefaultProject, "proj-1")
	}
}

func TestLoad_InvalidYAML(t *testing.T) {
	dir := t.TempDir()
	content := []byte(":\n  :\n  invalid: [[[")
	if err := os.WriteFile(filepath.Join(dir, configFileName), content, 0600); err != nil {
		t.Fatal(err)
	}

	fc := NewFileConfig(dir)
	_, err := fc.Load()
	if err == nil {
		t.Fatal("Load() expected error for invalid YAML, got nil")
	}
}

func TestLoad_UnreadableFile(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, configFileName)
	if err := os.WriteFile(path, []byte("server_name: x"), 0600); err != nil {
		t.Fatal(err)
	}
	// Remove read permission.
	if err := os.Chmod(path, 0000); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { os.Chmod(path, 0600) })

	fc := NewFileConfig(dir)
	_, err := fc.Load()
	if err == nil {
		t.Fatal("Load() expected error for unreadable file, got nil")
	}
}

func TestSave_Success(t *testing.T) {
	dir := t.TempDir()
	fc := NewFileConfig(filepath.Join(dir, "sub", "nested"))

	cfg := domain.Config{
		ServerName:     "fleet.example.com",
		ProxyAddress:   "localhost:8443",
		DefaultProject: "proj-2",
	}
	if err := fc.Save(cfg); err != nil {
		t.Fatalf("Save() error: %v", err)
	}

	// Verify file was written.
	data, err := os.ReadFile(filepath.Join(dir, "sub", "nested", configFileName))
	if err != nil {
		t.Fatalf("ReadFile error: %v", err)
	}
	if len(data) == 0 {
		t.Fatal("config file is empty after Save")
	}
}

func TestSave_ThenLoad_Roundtrip(t *testing.T) {
	dir := t.TempDir()
	fc := NewFileConfig(dir)

	want := domain.Config{
		ServerName:     "fleet.test",
		ProxyAddress:   "127.0.0.1:9090",
		DefaultProject: "my-project",
	}
	if err := fc.Save(want); err != nil {
		t.Fatalf("Save() error: %v", err)
	}

	got, err := fc.Load()
	if err != nil {
		t.Fatalf("Load() error: %v", err)
	}
	if got != want {
		t.Errorf("roundtrip mismatch: got %+v, want %+v", got, want)
	}
}

func TestSave_UnwritableDirectory(t *testing.T) {
	dir := t.TempDir()
	locked := filepath.Join(dir, "locked")
	if err := os.Mkdir(locked, 0500); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { os.Chmod(locked, 0700) })

	// The config file path sits inside locked/subdir/ which cannot be created.
	fc := NewFileConfig(filepath.Join(locked, "subdir"))

	err := fc.Save(domain.Config{ServerName: "x"})
	if err == nil {
		t.Fatal("Save() expected error when directory is not writable, got nil")
	}
}
