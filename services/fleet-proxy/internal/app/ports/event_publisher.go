package ports

import "github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/event"

// EventPublisher is a port for publishing domain events to an in-process
// event bus. It is used by interceptors and adapters to emit observability
// events (e.g., rpc.inbound, rpc.outbound) without depending on external
// infrastructure.
type EventPublisher interface {
	Publish(evt event.FleetEvent)
}
