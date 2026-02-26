// Package planning provides an adapter implementing ports.PlanningClient.
// Currently operates as a configurable stub that can report its connection
// status. The real gRPC transport will be wired in when proto stubs are
// generated for the planning service (fleet.planning.v2).
package planning

import (
	"context"
	"fmt"
	"log/slog"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

// Client is the planning service adapter. It stores the upstream gRPC address
// and tracks connection state. When connected is false, all methods return
// errNotConnected, making it safe to start the proxy before the planning
// service is available.
type Client struct {
	addr      string
	connected bool
}

// NewClient creates a planning Client targeting the given address. The client
// starts in disconnected mode. Call Connect() to enable request forwarding
// once the upstream service is reachable.
func NewClient(addr string) *Client {
	slog.Info("planning client created", "addr", addr, "connected", false)
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
// this would establish the gRPC connection to the upstream planning service
// using the fleet.planning.v2 proto.
func (c *Client) Connect() {
	c.connected = true
	slog.Info("planning client connected", "addr", c.addr)
}

// Disconnect transitions the client to disconnected mode.
func (c *Client) Disconnect() {
	c.connected = false
	slog.Info("planning client disconnected", "addr", c.addr)
}

var errNotConnected = fmt.Errorf("planning client not connected")

// CreateProject creates a new project and returns its ID.
func (c *Client) CreateProject(_ context.Context, _, _ string) (string, error) {
	if !c.connected {
		return "", errNotConnected
	}
	return "", fmt.Errorf("planning gRPC transport not yet implemented (addr=%s)", c.addr)
}

// CreateEpic creates a new epic under a project and returns its ID.
func (c *Client) CreateEpic(_ context.Context, _, _, _ string) (string, error) {
	if !c.connected {
		return "", errNotConnected
	}
	return "", fmt.Errorf("planning gRPC transport not yet implemented (addr=%s)", c.addr)
}

// CreateStory creates a new story under an epic and returns its ID.
func (c *Client) CreateStory(_ context.Context, _, _, _ string) (string, error) {
	if !c.connected {
		return "", errNotConnected
	}
	return "", fmt.Errorf("planning gRPC transport not yet implemented (addr=%s)", c.addr)
}

// TransitionStory moves a story to a new state.
func (c *Client) TransitionStory(_ context.Context, _, _ string) error {
	if !c.connected {
		return errNotConnected
	}
	return fmt.Errorf("planning gRPC transport not yet implemented (addr=%s)", c.addr)
}

// CreateTask creates a new task under a story and returns its ID.
func (c *Client) CreateTask(_ context.Context, _, _, _, _, _ string, _, _ int32) (string, error) {
	if !c.connected {
		return "", errNotConnected
	}
	return "", fmt.Errorf("planning gRPC transport not yet implemented (addr=%s)", c.addr)
}

// ApproveDecision approves a pending decision on a story.
func (c *Client) ApproveDecision(_ context.Context, _, _, _ string) error {
	if !c.connected {
		return errNotConnected
	}
	return fmt.Errorf("planning gRPC transport not yet implemented (addr=%s)", c.addr)
}

// RejectDecision rejects a pending decision on a story.
func (c *Client) RejectDecision(_ context.Context, _, _, _ string) error {
	if !c.connected {
		return errNotConnected
	}
	return fmt.Errorf("planning gRPC transport not yet implemented (addr=%s)", c.addr)
}

// ListProjects returns a page of projects matching the filter.
func (c *Client) ListProjects(_ context.Context, _ string, _, _ int32) ([]ports.ProjectResult, int32, error) {
	if !c.connected {
		return nil, 0, errNotConnected
	}
	return nil, 0, fmt.Errorf("planning gRPC transport not yet implemented (addr=%s)", c.addr)
}

// ListEpics returns a page of epics for a project matching the filter.
func (c *Client) ListEpics(_ context.Context, _, _ string, _, _ int32) ([]ports.EpicResult, int32, error) {
	if !c.connected {
		return nil, 0, errNotConnected
	}
	return nil, 0, fmt.Errorf("planning gRPC transport not yet implemented (addr=%s)", c.addr)
}

// ListStories returns a page of stories for an epic matching the filter.
func (c *Client) ListStories(_ context.Context, _, _ string, _, _ int32) ([]ports.StoryResult, int32, error) {
	if !c.connected {
		return nil, 0, errNotConnected
	}
	return nil, 0, fmt.Errorf("planning gRPC transport not yet implemented (addr=%s)", c.addr)
}

// ListTasks returns a page of tasks for a story matching the filter.
func (c *Client) ListTasks(_ context.Context, _, _ string, _, _ int32) ([]ports.TaskResult, int32, error) {
	if !c.connected {
		return nil, 0, errNotConnected
	}
	return nil, 0, fmt.Errorf("planning gRPC transport not yet implemented (addr=%s)", c.addr)
}
