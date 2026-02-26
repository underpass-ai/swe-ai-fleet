package config

import (
	"fmt"
	"os"
	"path/filepath"

	"gopkg.in/yaml.v3"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

const (
	configFileName = "config.yaml"
	dirPermission  = 0700
	filePermission = 0600
)

// FileConfig implements ports.ConfigStore by persisting fleetctl
// configuration as a YAML file under baseDir/config.yaml.
type FileConfig struct {
	path string // full path to config.yaml
}

// NewFileConfig creates a FileConfig that reads and writes
// baseDir/config.yaml.
func NewFileConfig(baseDir string) *FileConfig {
	return &FileConfig{
		path: filepath.Join(baseDir, configFileName),
	}
}

// Load reads the configuration file and returns a Config value.
// If the file does not exist, it returns a zero-value Config (no error)
// so that first-run scenarios work without requiring prior setup.
func (c *FileConfig) Load() (domain.Config, error) {
	data, err := os.ReadFile(c.path)
	if err != nil {
		if os.IsNotExist(err) {
			return domain.Config{}, nil
		}
		return domain.Config{}, fmt.Errorf("read config %s: %w", c.path, err)
	}

	var cfg domain.Config
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return domain.Config{}, fmt.Errorf("parse config %s: %w", c.path, err)
	}

	return cfg, nil
}

// Save writes the given Config to the configuration file, creating
// parent directories as needed.
func (c *FileConfig) Save(cfg domain.Config) error {
	dir := filepath.Dir(c.path)
	if err := os.MkdirAll(dir, dirPermission); err != nil {
		return fmt.Errorf("create config directory: %w", err)
	}

	data, err := yaml.Marshal(cfg)
	if err != nil {
		return fmt.Errorf("marshal config: %w", err)
	}

	if err := os.WriteFile(c.path, data, filePermission); err != nil {
		return fmt.Errorf("write config %s: %w", c.path, err)
	}

	return nil
}
