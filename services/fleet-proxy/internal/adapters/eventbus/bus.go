// Package eventbus provides an in-process event bus that implements both
// ports.EventPublisher (write side) and ports.EventSubscriber (read side).
// It is used to merge locally-generated RPC trace events with NATS-sourced
// domain events before streaming them to fleetctl clients.
package eventbus

import (
	"context"
	"log/slog"
	"sync"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/event"
)

// subscriberBufSize is the buffer size for each subscriber channel.
const subscriberBufSize = 256

// subscriber is a registered event consumer.
type subscriber struct {
	ch     chan event.FleetEvent
	filter event.EventFilter
}

// Bus is an in-process fan-out event bus. It implements ports.EventPublisher
// and ports.EventSubscriber.
type Bus struct {
	mu          sync.RWMutex
	subscribers []*subscriber
	closed      bool
}

// New creates a new in-process event bus.
func New() *Bus {
	return &Bus{}
}

// Publish sends an event to all active subscribers whose filters match.
// Non-blocking: if a subscriber's buffer is full the event is dropped for
// that subscriber (back-pressure).
func (b *Bus) Publish(evt event.FleetEvent) {
	b.mu.RLock()
	defer b.mu.RUnlock()

	if b.closed {
		return
	}

	for _, sub := range b.subscribers {
		if !sub.filter.Matches(evt) {
			continue
		}
		select {
		case sub.ch <- evt:
		default:
			slog.Warn("eventbus: dropped event for slow subscriber",
				"type", evt.Type.String())
		}
	}
}

// Subscribe creates a new filtered subscription. The returned channel
// delivers events until ctx is cancelled or Close is called.
func (b *Bus) Subscribe(ctx context.Context, filter event.EventFilter) (<-chan event.FleetEvent, error) {
	b.mu.Lock()
	if b.closed {
		b.mu.Unlock()
		ch := make(chan event.FleetEvent)
		close(ch)
		return ch, nil
	}

	sub := &subscriber{
		ch:     make(chan event.FleetEvent, subscriberBufSize),
		filter: filter,
	}
	b.subscribers = append(b.subscribers, sub)
	b.mu.Unlock()

	// Unregister when context is cancelled.
	go func() {
		<-ctx.Done()
		b.unsubscribe(sub)
	}()

	return sub.ch, nil
}

// Close shuts down the bus, closing all subscriber channels.
func (b *Bus) Close() error {
	b.mu.Lock()
	defer b.mu.Unlock()

	if b.closed {
		return nil
	}
	b.closed = true

	for _, sub := range b.subscribers {
		close(sub.ch)
	}
	b.subscribers = nil
	return nil
}

// unsubscribe removes a subscriber from the bus and closes its channel.
func (b *Bus) unsubscribe(target *subscriber) {
	b.mu.Lock()
	defer b.mu.Unlock()

	for i, sub := range b.subscribers {
		if sub == target {
			close(sub.ch)
			b.subscribers = append(b.subscribers[:i], b.subscribers[i+1:]...)
			return
		}
	}
}
