package ports

import (
	"context"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/event"
)

// EventSubscriber is a port for subscribing to domain events produced by the
// fleet (e.g., story transitions, ceremony completions). The adapter typically
// connects to NATS JetStream or a similar messaging system.
type EventSubscriber interface {
	// Subscribe opens a filtered event stream. The returned channel delivers
	// events until the context is cancelled or Close is called.
	Subscribe(ctx context.Context, filter event.EventFilter) (<-chan event.FleetEvent, error)

	// Close tears down all active subscriptions and releases resources.
	Close() error
}
