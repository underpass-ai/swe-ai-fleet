package domain

// Config holds the fleetctl client configuration. It is persisted as YAML
// under ~/.fleetctl/config.yaml (or $FLEETCTL_CONFIG).
type Config struct {
	ServerName     string `yaml:"server_name"`
	ProxyAddress   string `yaml:"proxy_address"`
	DefaultProject string `yaml:"default_project,omitempty"`
}
