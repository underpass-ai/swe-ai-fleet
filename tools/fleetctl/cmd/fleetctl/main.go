package main

import (
	"context"
	"flag"
	"fmt"
	"os"
	"path/filepath"

	tea "github.com/charmbracelet/bubbletea"

	configadapter "github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/adapters/config"
	grpcadapter "github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/adapters/grpc"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/adapters/pki"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/command"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/tui"
)

// version is set at build time via -ldflags.
var version = "dev"

func main() {
	if err := run(); err != nil {
		fmt.Fprintf(os.Stderr, "fleetctl: %v\n", err)
		os.Exit(1)
	}
}

func run() error {
	configDir := configBaseDir()

	// Handle subcommands before any setup.
	if len(os.Args) > 1 {
		switch os.Args[1] {
		case "version":
			fmt.Printf("fleetctl %s\n", version)
			return nil
		case "help", "--help", "-h":
			printUsage()
			return nil
		case "enroll":
			return runEnroll(configDir)
		}
	}

	// Load configuration.
	cfgStore := configadapter.NewFileConfig(configDir)
	cfg, err := cfgStore.Load()
	if err != nil {
		return fmt.Errorf("load config: %w", err)
	}

	// Check credentials.
	credStore := pki.NewFileStore(configDir)
	if !credStore.Exists() {
		fmt.Fprintln(os.Stderr, "No credentials found. Run 'fleetctl enroll' first.")
		return nil
	}

	creds, err := credStore.Load()
	if err != nil {
		return fmt.Errorf("load credentials: %w", err)
	}

	if creds.IsExpired() {
		fmt.Fprintln(os.Stderr, "Warning: credentials have expired. Run 'fleetctl enroll' to renew.")
	}

	// Determine proxy address.
	target := cfg.ProxyAddress
	if target == "" {
		target = "localhost:8443"
	}

	// Establish gRPC connection with mTLS.
	ctx := context.Background()
	conn, err := grpcadapter.Dial(ctx, target, creds)
	if err != nil {
		return fmt.Errorf("connect to fleet-proxy: %w", err)
	}
	defer conn.Close()

	client := grpcadapter.NewFleetClient(conn)

	// Launch the TUI.
	model := tui.NewModel(client)
	p := tea.NewProgram(model, tea.WithAltScreen())
	if _, err := p.Run(); err != nil {
		return fmt.Errorf("tui: %w", err)
	}

	return nil
}

// runEnroll handles the "fleetctl enroll" subcommand. It exchanges an API key
// for mTLS credentials and persists them locally.
func runEnroll(configDir string) error {
	fs := flag.NewFlagSet("enroll", flag.ContinueOnError)
	apiKey := fs.String("api-key", "", "enrollment API key (required, format: keyID:secret)")
	server := fs.String("server", "fleet.underpassai.com:443", "fleet-proxy gRPC address")
	deviceID := fs.String("device-id", "", "device identifier (default: hostname)")
	serverName := fs.String("server-name", "fleet.underpassai.com", "TLS server name for certificate verification")
	caCertPath := fs.String("ca-cert", "", "path to CA certificate for server TLS verification")
	insecure := fs.Bool("insecure", false, "skip TLS server verification (dev/testing only)")

	if err := fs.Parse(os.Args[2:]); err != nil {
		if err == flag.ErrHelp {
			return nil
		}
		return err
	}

	if *apiKey == "" {
		fs.Usage()
		return fmt.Errorf("--api-key is required")
	}

	if *deviceID == "" {
		hostname, err := os.Hostname()
		if err != nil {
			hostname = "unknown"
		}
		*deviceID = hostname
	}

	// Save config before enrollment — the handler reads server_name from
	// config to persist alongside credentials.
	cfgStore := configadapter.NewFileConfig(configDir)
	cfg := domain.Config{
		ServerName:   *serverName,
		ProxyAddress: *server,
	}
	if err := cfgStore.Save(cfg); err != nil {
		return fmt.Errorf("save config: %w", err)
	}

	// Load CA certificate if provided.
	var caCertPEM []byte
	if *caCertPath != "" {
		data, err := os.ReadFile(*caCertPath)
		if err != nil {
			return fmt.Errorf("read CA cert %s: %w", *caCertPath, err)
		}
		caCertPEM = data
	}

	// Establish TLS-only connection (no client cert — not enrolled yet).
	ctx := context.Background()
	conn, err := grpcadapter.DialEnrollment(ctx, *server, caCertPEM, *serverName, *insecure)
	if err != nil {
		return fmt.Errorf("connect to %s: %w", *server, err)
	}
	defer conn.Close()

	// Wire the enrollment handler and execute.
	client := grpcadapter.NewFleetClient(conn)
	credStore := pki.NewFileStore(configDir)
	handler := command.NewEnrollHandler(client, credStore, cfgStore)

	fmt.Fprintf(os.Stderr, "Enrolling device %q with %s ...\n", *deviceID, *server)

	result, err := handler.Handle(ctx, command.EnrollCmd{
		APIKey:   *apiKey,
		DeviceID: *deviceID,
	})
	if err != nil {
		return err
	}

	fmt.Fprintf(os.Stderr, "Enrolled successfully.\n")
	fmt.Fprintf(os.Stderr, "  Client ID:   %s\n", result.ClientID)
	fmt.Fprintf(os.Stderr, "  Expires at:  %s\n", result.ExpiresAt)
	fmt.Fprintf(os.Stderr, "  Credentials: %s\n", filepath.Join(configDir, "pki"))
	return nil
}

// configBaseDir returns the base directory for fleetctl configuration
// and credentials, respecting XDG_CONFIG_HOME.
func configBaseDir() string {
	if xdg := os.Getenv("XDG_CONFIG_HOME"); xdg != "" {
		return filepath.Join(xdg, "fleetctl")
	}
	home, err := os.UserHomeDir()
	if err != nil {
		// Fallback if home directory cannot be determined.
		return filepath.Join(".", ".config", "fleetctl")
	}
	return filepath.Join(home, ".config", "fleetctl")
}

func printUsage() {
	fmt.Println("fleetctl - SWE AI Fleet command-line interface")
	fmt.Println()
	fmt.Println("Usage:")
	fmt.Println("  fleetctl              Launch the interactive TUI")
	fmt.Println("  fleetctl enroll       Enroll this device with the fleet control plane")
	fmt.Println("  fleetctl version      Print version information")
	fmt.Println("  fleetctl help         Show this help message")
}
