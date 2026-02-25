package query

import (
	"context"
	"errors"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/event"
)

// WatchEventsQuery carries the parameters for subscribing to fleet events.
type WatchEventsQuery struct {
	Filter event.EventFilter
}

// WatchEventsHandler handles event subscription queries. Unlike other query
// handlers it returns a channel rather than a result struct, because the
// caller is expected to consume events as a long-lived stream.
type WatchEventsHandler struct {
	subscriber ports.EventSubscriber
}

// NewWatchEventsHandler wires the handler to the event subscriber port.
func NewWatchEventsHandler(s ports.EventSubscriber) *WatchEventsHandler {
	return &WatchEventsHandler{subscriber: s}
}

// Handle validates the query and opens an event subscription. The returned
// channel delivers events until the context is cancelled or the subscriber
// is closed.
func (h *WatchEventsHandler) Handle(ctx context.Context, q WatchEventsQuery) (<-chan event.FleetEvent, error) {
	// The EventFilter constructor already validates that at least one
	// criterion is set, but we guard against a zero-value filter being
	// passed directly without going through NewEventFilter.
	if len(q.Filter.Types) == 0 && q.Filter.ProjectID == nil {
		return nil, errors.New("event filter must specify at least one type or project ID")
	}

	return h.subscriber.Subscribe(ctx, q.Filter)
}
