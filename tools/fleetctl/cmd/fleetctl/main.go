package main

import (
	"context"
	"fmt"
	"os"
	"path/filepath"

	tea "github.com/charmbracelet/bubbletea"

	configadapter "github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/adapters/config"
	grpcadapter "github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/adapters/grpc"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/adapters/pki"
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
			fmt.Fprintln(os.Stderr, "Enrollment will be implemented in Phase 2.")
			fmt.Fprintln(os.Stderr, "Usage: fleetctl enroll --api-key <key> --server <addr>")
			return nil
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
