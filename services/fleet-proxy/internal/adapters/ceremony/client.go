// Package ceremony provides an adapter implementing ports.CeremonyClient.
// Currently operates as a configurable stub that can report its connection
// status. The real gRPC transport will be wired in when proto stubs are
// generated for the ceremony service.
package ceremony

import (
	"context"
	"fmt"
	"log/slog"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

// Client is the ceremony service adapter. It stores the upstream gRPC address
// and tracks connection state. When connected is false, all methods return
// errNotConnected, making it safe to start the proxy before the ceremony
// service is available.
type Client struct {
	addr      string
	connected bool
}

// NewClient creates a ceremony Client targeting the given address. The client
// starts in disconnected mode. Call Connect() to enable request forwarding
// once the upstream service is reachable.
func NewClient(addr string) *Client {
	slog.Info("ceremony client created", "addr", addr, "connected", false)
	return &Client{addr: addr, connected: false}
}

// Addr returns the configured upstream address.
func (c *Client) Addr() string {
	return c.addr
}

// Connected reports whether the client is in connected mode.
func (c *Client) Connected() bool {
	return c.connected
}

// Connect transitions the client to connected mode. In a real implementation,
// this would establish the gRPC connection to the upstream ceremony service.
func (c *Client) Connect() {
	c.connected = true
	slog.Info("ceremony client connected", "addr", c.addr)
}

// Disconnect transitions the client to disconnected mode.
func (c *Client) Disconnect() {
	c.connected = false
	slog.Info("ceremony client disconnected", "addr", c.addr)
}

var errNotConnected = fmt.Errorf("ceremony client not connected")

// StartCeremony starts a ceremony instance and returns the instance ID.
func (c *Client) StartCeremony(_ context.Context, _, _, _ string, _ []string) (string, error) {
	if !c.connected {
		return "", errNotConnected
	}
	// TODO: forward via gRPC to the upstream ceremony service.
	return "", fmt.Errorf("ceremony gRPC transport not yet implemented (addr=%s)", c.addr)
}

// StartBacklogReview starts a backlog review ceremony and returns the review count.
func (c *Client) StartBacklogReview(_ context.Context, _ string) (int32, error) {
	if !c.connected {
		return 0, errNotConnected
	}
	return 0, fmt.Errorf("ceremony gRPC transport not yet implemented (addr=%s)", c.addr)
}

// GetCeremony fetches a ceremony instance by its instance ID.
func (c *Client) GetCeremony(_ context.Context, _ string) (ports.CeremonyResult, error) {
	if !c.connected {
		return ports.CeremonyResult{}, errNotConnected
	}
	return ports.CeremonyResult{}, fmt.Errorf("ceremony gRPC transport not yet implemented (addr=%s)", c.addr)
}

// ListCeremonies returns a page of ceremonies matching the filter.
func (c *Client) ListCeremonies(_ context.Context, _, _ string, _, _ int32) ([]ports.CeremonyResult, int32, error) {
	if !c.connected {
		return nil, 0, errNotConnected
	}
	return nil, 0, fmt.Errorf("ceremony gRPC transport not yet implemented (addr=%s)", c.addr)
}
