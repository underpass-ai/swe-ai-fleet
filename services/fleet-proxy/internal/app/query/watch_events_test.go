package query

import (
	"context"
	"errors"
	"strings"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/event"
)

func TestWatchEventsHandler_Handle(t *testing.T) {
	t.Parallel()

	projectID := "proj-1"

	tests := []struct {
		name       string
		query      WatchEventsQuery
		subscriber *fakeEventSubscriber
		wantErr    bool
		errSubstr  string
		wantEvents int
	}{
		{
			name: "successful watch with type filter",
			query: WatchEventsQuery{
				Filter: event.EventFilter{
					Types: []event.EventType{event.EventStoryCreated},
				},
			},
			subscriber: &fakeEventSubscriber{
				ch: make(chan event.FleetEvent, 2),
			},
			wantEvents: 0, // channel is empty but valid
		},
		{
			name: "successful watch with project ID filter",
			query: WatchEventsQuery{
				Filter: event.EventFilter{
					ProjectID: &projectID,
				},
			},
			subscriber: &fakeEventSubscriber{
				ch: make(chan event.FleetEvent, 1),
			},
		},
		{
			name: "successful watch with both filters",
			query: WatchEventsQuery{
				Filter: event.EventFilter{
					Types:     []event.EventType{event.EventCeremonyStarted},
					ProjectID: &projectID,
				},
			},
			subscriber: &fakeEventSubscriber{
				ch: make(chan event.FleetEvent, 1),
			},
		},
		{
			name: "empty filter (no types, no project ID)",
			query: WatchEventsQuery{
				Filter: event.EventFilter{},
			},
			subscriber: &fakeEventSubscriber{
				ch: make(chan event.FleetEvent),
			},
			wantErr:   true,
			errSubstr: "event filter must specify at least one type or project ID",
		},
		{
			name: "subscriber error",
			query: WatchEventsQuery{
				Filter: event.EventFilter{
					Types: []event.EventType{event.EventTaskCreated},
				},
			},
			subscriber: &fakeEventSubscriber{
				err: errors.New("NATS connection failed"),
			},
			wantErr:   true,
			errSubstr: "NATS connection failed",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			handler := NewWatchEventsHandler(tt.subscriber)

			ch, err := handler.Handle(context.Background(), tt.query)

			if tt.wantErr {
				if err == nil {
					t.Fatalf("Handle() expected error containing %q, got nil", tt.errSubstr)
				}
				if !strings.Contains(err.Error(), tt.errSubstr) {
					t.Fatalf("Handle() error = %q, want substring %q", err.Error(), tt.errSubstr)
				}
				if ch != nil {
					t.Error("Handle() returned non-nil channel on error")
				}
				return
			}

			if err != nil {
				t.Fatalf("Handle() unexpected error: %v", err)
			}

			if ch == nil {
				t.Fatal("Handle() returned nil channel on success")
			}
		})
	}
}

func TestWatchEventsHandler_Handle_ReceivesEvents(t *testing.T) {
	t.Parallel()

	evtCh := make(chan event.FleetEvent, 2)

	// Pre-populate events in the channel.
	evt1, err := event.NewFleetEvent(event.EventStoryCreated, "idem-1", "corr-1", "test", []byte("{}"))
	if err != nil {
		t.Fatalf("NewFleetEvent: %v", err)
	}
	evt2, err := event.NewFleetEvent(event.EventTaskCreated, "idem-2", "corr-1", "test", []byte("{}"))
	if err != nil {
		t.Fatalf("NewFleetEvent: %v", err)
	}
	evtCh <- evt1
	evtCh <- evt2

	subscriber := &fakeEventSubscriber{ch: evtCh}
	handler := NewWatchEventsHandler(subscriber)

	ch, err := handler.Handle(context.Background(), WatchEventsQuery{
		Filter: event.EventFilter{
			Types: []event.EventType{event.EventStoryCreated, event.EventTaskCreated},
		},
	})
	if err != nil {
		t.Fatalf("Handle() unexpected error: %v", err)
	}

	// Read events from the channel.
	received1 := <-ch
	if received1.Type != event.EventStoryCreated {
		t.Errorf("first event Type = %q, want %q", received1.Type, event.EventStoryCreated)
	}

	received2 := <-ch
	if received2.Type != event.EventTaskCreated {
		t.Errorf("second event Type = %q, want %q", received2.Type, event.EventTaskCreated)
	}
}
