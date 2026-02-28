package eventbus

import (
	"context"
	"sort"
	"testing"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/event"
)

// fakeSubscriber is a minimal EventSubscriber for testing.
type fakeSubscriber struct {
	ch chan event.FleetEvent
}

func (f *fakeSubscriber) Subscribe(_ context.Context, _ event.EventFilter) (<-chan event.FleetEvent, error) {
	return f.ch, nil
}

func (f *fakeSubscriber) Close() error {
	return nil
}

func TestMergingSubscriber_MergesEvents(t *testing.T) {
	ch1 := make(chan event.FleetEvent, 4)
	ch2 := make(chan event.FleetEvent, 4)

	src1 := &fakeSubscriber{ch: ch1}
	src2 := &fakeSubscriber{ch: ch2}

	m := NewMerging(src1, src2)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	filter := event.EventFilter{Types: []event.EventType{event.EventRPCInbound, event.EventRPCOutbound}}
	merged, err := m.Subscribe(ctx, filter)
	if err != nil {
		t.Fatalf("Subscribe() error = %v", err)
	}

	ch1 <- event.FleetEvent{Type: event.EventRPCInbound, IdempotencyKey: "a"}
	ch2 <- event.FleetEvent{Type: event.EventRPCOutbound, IdempotencyKey: "b"}

	// Close source channels so goroutines finish.
	close(ch1)
	close(ch2)

	var got []string
	for evt := range merged {
		got = append(got, evt.IdempotencyKey)
	}

	sort.Strings(got)
	if len(got) != 2 || got[0] != "a" || got[1] != "b" {
		t.Errorf("got keys %v, want [a b]", got)
	}
}

func TestMergingSubscriber_ContextCancellation(t *testing.T) {
	ch1 := make(chan event.FleetEvent, 4)
	src1 := &fakeSubscriber{ch: ch1}

	m := NewMerging(src1)

	ctx, cancel := context.WithCancel(context.Background())
	merged, err := m.Subscribe(ctx, event.EventFilter{Types: []event.EventType{event.EventRPCInbound}})
	if err != nil {
		t.Fatalf("Subscribe() error = %v", err)
	}

	cancel()
	// Give goroutines time to exit.
	time.Sleep(50 * time.Millisecond)
	close(ch1)

	// Drain anything remaining; channel should close.
	for range merged {
		// Consume residual events.
	}
}
