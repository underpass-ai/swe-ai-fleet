package eventbus

import (
	"context"
	"testing"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/event"
)

func makeEvent(t event.EventType) event.FleetEvent {
	return event.FleetEvent{
		Type:           t,
		IdempotencyKey: "key-1",
		CorrelationID:  "corr-1",
		Timestamp:      time.Now(),
		Producer:       "test",
	}
}

func TestBus_PublishWithNoSubscribers(t *testing.T) {
	bus := New()
	defer bus.Close()

	// Should not panic.
	bus.Publish(makeEvent(event.EventRPCInbound))
}

func TestBus_SingleSubscriber(t *testing.T) {
	bus := New()
	defer bus.Close()

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	filter := event.EventFilter{Types: []event.EventType{event.EventRPCInbound}}
	ch, err := bus.Subscribe(ctx, filter)
	if err != nil {
		t.Fatalf("Subscribe() error = %v", err)
	}

	bus.Publish(makeEvent(event.EventRPCInbound))

	select {
	case evt := <-ch:
		if evt.Type != event.EventRPCInbound {
			t.Errorf("got type %s, want %s", evt.Type, event.EventRPCInbound)
		}
	case <-time.After(time.Second):
		t.Fatal("timed out waiting for event")
	}
}

func TestBus_FilteredOut(t *testing.T) {
	bus := New()
	defer bus.Close()

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	filter := event.EventFilter{Types: []event.EventType{event.EventRPCOutbound}}
	ch, err := bus.Subscribe(ctx, filter)
	if err != nil {
		t.Fatalf("Subscribe() error = %v", err)
	}

	bus.Publish(makeEvent(event.EventRPCInbound))

	select {
	case evt := <-ch:
		t.Fatalf("expected no event, got %v", evt)
	case <-time.After(50 * time.Millisecond):
		// OK — event was filtered out.
	}
}

func TestBus_MultipleSubscribers(t *testing.T) {
	bus := New()
	defer bus.Close()

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	allFilter := event.EventFilter{Types: []event.EventType{event.EventRPCInbound, event.EventRPCOutbound}}

	ch1, err := bus.Subscribe(ctx, allFilter)
	if err != nil {
		t.Fatalf("Subscribe ch1 error = %v", err)
	}
	ch2, err := bus.Subscribe(ctx, allFilter)
	if err != nil {
		t.Fatalf("Subscribe ch2 error = %v", err)
	}

	bus.Publish(makeEvent(event.EventRPCInbound))

	for _, ch := range []<-chan event.FleetEvent{ch1, ch2} {
		select {
		case evt := <-ch:
			if evt.Type != event.EventRPCInbound {
				t.Errorf("got type %s, want %s", evt.Type, event.EventRPCInbound)
			}
		case <-time.After(time.Second):
			t.Fatal("timed out waiting for event")
		}
	}
}

func TestBus_ContextCancellation(t *testing.T) {
	bus := New()
	defer bus.Close()

	ctx, cancel := context.WithCancel(context.Background())
	filter := event.EventFilter{Types: []event.EventType{event.EventRPCInbound}}
	ch, err := bus.Subscribe(ctx, filter)
	if err != nil {
		t.Fatalf("Subscribe() error = %v", err)
	}

	cancel()
	// Give the goroutine time to unsubscribe.
	time.Sleep(50 * time.Millisecond)

	// Channel should be closed.
	select {
	case _, ok := <-ch:
		if ok {
			t.Fatal("expected channel to be closed after context cancellation")
		}
	case <-time.After(time.Second):
		t.Fatal("timed out waiting for channel close")
	}
}

func TestBus_CloseClosesChannels(t *testing.T) {
	bus := New()

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	filter := event.EventFilter{Types: []event.EventType{event.EventRPCInbound}}
	ch, err := bus.Subscribe(ctx, filter)
	if err != nil {
		t.Fatalf("Subscribe() error = %v", err)
	}

	bus.Close()

	select {
	case _, ok := <-ch:
		if ok {
			t.Fatal("expected channel to be closed after bus.Close()")
		}
	case <-time.After(time.Second):
		t.Fatal("timed out waiting for channel close")
	}
}
