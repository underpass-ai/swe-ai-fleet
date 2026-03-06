# fleetctl

Terminal UI (TUI) client for the SWE AI Fleet control plane. Connects to
`fleet-proxy` via `kubectl port-forward` + mTLS.

## Features

- Real-time event feed from NATS JetStream (via server-streaming gRPC)
- Project, Epic, Story, and Task management
- Story FSM state transitions with ASCII state machine visualization
- Ceremony monitoring with live step status
- mTLS enrollment wizard with ECDSA P-256 client certificates
- Vim-style keyboard navigation

## Quick Start

### 1. Port-forward the fleet-proxy

```bash
kubectl port-forward -n swe-ai-fleet svc/fleet-proxy 8443:8443
```

### 2. Enroll (first-time setup)

```bash
fleetctl enroll --api-key=<key>
```

This generates an ECDSA P-256 keypair, sends a CSR to the proxy, and saves the
signed certificate to `~/.config/fleetctl/pki/`.

### 3. Launch TUI

```bash
fleetctl
```

## Navigation

| Key | Action |
|-----|--------|
| `p` | Projects view |
| `s` | Stories view |
| `t` | Tasks view |
| `c` | Ceremonies view |
| `e` | Events stream |
| `esc` | Back to dashboard |
| `n` | Create new (in list views) |
| `r` | Refresh |
| `q` / `ctrl+c` | Quit |

## Build

```bash
make build      # Binary at bin/fleetctl
make install    # Install to $GOPATH/bin
make test       # Run unit tests
```

## Configuration

Config and credentials are stored in `~/.config/fleetctl/`:

```
~/.config/fleetctl/
├── config.yaml          # server_name, proxy_address, default_project
└── pki/
    ├── client.key       # ECDSA P-256 private key (0600)
    ├── client.crt       # Signed client certificate (24h TTL)
    ├── ca.crt           # CA chain for server verification
    └── server_name      # Expected server SAN for TLS verification
```

The `XDG_CONFIG_HOME` environment variable is respected.

### config.yaml

```yaml
server_name: fleet-proxy.swe-ai-fleet.svc.cluster.local
proxy_address: localhost:8443
default_project: my-project
```

## TLS Verification

When connecting through `kubectl port-forward`, fleetctl connects to
`localhost:8443` but verifies the server certificate against the cluster DNS
name (`fleet-proxy.swe-ai-fleet.svc.cluster.local`). This is handled
automatically via the `ServerName` override in the TLS config.

## Architecture

```
tools/fleetctl/
├── cmd/fleetctl/          # Entry point
├── internal/
│   ├── domain/            # Read models + value objects
│   │   └── identity/      # Credentials, ServerName
│   ├── app/               # Application layer (CQRS)
│   │   ├── command/       # Enroll, CreateProject, CreateStory, etc.
│   │   ├── query/         # ListProjects, ListStories, WatchEvents, etc.
│   │   └── ports/         # FleetClient, CredentialStore, ConfigStore
│   ├── adapters/          # Infrastructure
│   │   ├── grpc/          # gRPC client with mTLS
│   │   ├── pki/           # Local cert file store
│   │   └── config/        # YAML config file
│   └── tui/               # Bubble Tea UI
│       ├── views/         # Dashboard, Projects, Stories, Tasks, Ceremonies, Events, Enrollment
│       └── components/    # Table, StatusBar, Breadcrumb, Spinner, FSM Diagram
├── Makefile
├── go.mod
└── go.sum
```

## Dependencies

- [Bubble Tea](https://github.com/charmbracelet/bubbletea) - TUI framework
- [Lip Gloss](https://github.com/charmbracelet/lipgloss) - Styling
- [Bubbles](https://github.com/charmbracelet/bubbles) - TUI components (table, textinput, viewport, spinner)
- [gRPC-Go](https://google.golang.org/grpc) - gRPC client
