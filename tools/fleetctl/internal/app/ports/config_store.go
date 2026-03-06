package ports

import (
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// ConfigStore persists and retrieves fleetctl client configuration.
// The default implementation writes YAML to ~/.fleetctl/config.yaml.
type ConfigStore interface {
	// Load reads the configuration file and returns a Config value.
	Load() (domain.Config, error)

	// Save writes the given Config to the configuration file,
	// creating parent directories as needed.
	Save(cfg domain.Config) error
}
