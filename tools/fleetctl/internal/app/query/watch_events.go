package query

import (
	"context"
	"fmt"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// WatchEventsQuery carries the subscription parameters for the event stream.
type WatchEventsQuery struct {
	EventTypes []string
	ProjectID  string
}

// WatchEventsHandler opens a streaming subscription for fleet events and
// returns a channel that the caller (TUI or CLI) can range over.
type WatchEventsHandler struct {
	client ports.FleetClient
}

// NewWatchEventsHandler returns a handler wired to the given FleetClient.
func NewWatchEventsHandler(client ports.FleetClient) *WatchEventsHandler {
	return &WatchEventsHandler{client: client}
}

// Handle opens the event stream. The returned channel is closed when ctx
// is cancelled or the server terminates the stream. The caller is
// responsible for draining the channel.
func (h *WatchEventsHandler) Handle(ctx context.Context, q WatchEventsQuery) (<-chan domain.FleetEvent, error) {
	ch, err := h.client.WatchEvents(ctx, q.EventTypes, q.ProjectID)
	if err != nil {
		return nil, fmt.Errorf("watch_events: %w", err)
	}
	return ch, nil
}
