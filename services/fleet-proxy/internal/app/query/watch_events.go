package query

import (
	"context"

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

// Handle opens an event subscription. An empty filter (no types, no project ID)
// subscribes to all events. The returned channel delivers events until the
// context is cancelled or the subscriber is closed.
func (h *WatchEventsHandler) Handle(ctx context.Context, q WatchEventsQuery) (<-chan event.FleetEvent, error) {
	return h.subscriber.Subscribe(ctx, q.Filter)
}
