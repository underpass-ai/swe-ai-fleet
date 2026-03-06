package event

import (
	"strings"
	"testing"
	"time"
)

func TestNewEventFilter(t *testing.T) {
	t.Parallel()

	projectID := "proj-123"

	tests := []struct {
		name      string
		types     []EventType
		projectID *string
		wantErr   bool
		errSubstr string
	}{
		{
			name:  "valid with types only",
			types: []EventType{EventStoryCreated, EventTaskCreated},
		},
		{
			name:      "valid with projectID only",
			projectID: &projectID,
		},
		{
			name:      "valid with both types and projectID",
			types:     []EventType{EventCeremonyStarted},
			projectID: &projectID,
		},
		{
			name:      "invalid with neither types nor projectID",
			types:     nil,
			projectID: nil,
			wantErr:   true,
			errSubstr: "at least one criterion",
		},
		{
			name:      "invalid with empty types and nil projectID",
			types:     []EventType{},
			projectID: nil,
			wantErr:   true,
			errSubstr: "at least one criterion",
		},
		{
			name:      "invalid event type in list",
			types:     []EventType{EventStoryCreated, EventType("bad.type")},
			wantErr:   true,
			errSubstr: "invalid event type",
		},
		{
			name:      "empty project ID string",
			types:     nil,
			projectID: strPtr(""),
			wantErr:   true,
			errSubstr: "project ID cannot be an empty string",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			got, err := NewEventFilter(tt.types, tt.projectID)

			if tt.wantErr {
				if err == nil {
					t.Fatalf("NewEventFilter() expected error containing %q, got nil", tt.errSubstr)
				}
				if !strings.Contains(err.Error(), tt.errSubstr) {
					t.Fatalf("NewEventFilter() error = %q, want substring %q", err.Error(), tt.errSubstr)
				}
				return
			}

			if err != nil {
				t.Fatalf("NewEventFilter() unexpected error: %v", err)
			}

			// Sanity checks on the returned filter.
			if tt.types != nil && len(got.Types) != len(tt.types) {
				t.Errorf("Types length = %d, want %d", len(got.Types), len(tt.types))
			}
			if tt.projectID != nil && (got.ProjectID == nil || *got.ProjectID != *tt.projectID) {
				t.Errorf("ProjectID = %v, want %v", got.ProjectID, tt.projectID)
			}
		})
	}
}

func TestEventFilter_Matches(t *testing.T) {
	t.Parallel()

	storyEvt := FleetEvent{
		Type:           EventStoryCreated,
		IdempotencyKey: "key-1",
		CorrelationID:  "corr-1",
		Timestamp:      time.Now(),
		Producer:       "test",
		Payload:        []byte(`{}`),
	}

	taskEvt := FleetEvent{
		Type:           EventTaskCreated,
		IdempotencyKey: "key-2",
		CorrelationID:  "corr-2",
		Timestamp:      time.Now(),
		Producer:       "test",
		Payload:        []byte(`{}`),
	}

	ceremonyEvt := FleetEvent{
		Type:           EventCeremonyStarted,
		IdempotencyKey: "key-3",
		CorrelationID:  "corr-3",
		Timestamp:      time.Now(),
		Producer:       "test",
		Payload:        []byte(`{}`),
	}

	tests := []struct {
		name   string
		filter EventFilter
		event  FleetEvent
		match  bool
	}{
		{
			name:   "type filter matches story event",
			filter: EventFilter{Types: []EventType{EventStoryCreated}},
			event:  storyEvt,
			match:  true,
		},
		{
			name:   "type filter does not match task event",
			filter: EventFilter{Types: []EventType{EventStoryCreated}},
			event:  taskEvt,
			match:  false,
		},
		{
			name:   "multiple type filter matches ceremony event",
			filter: EventFilter{Types: []EventType{EventStoryCreated, EventCeremonyStarted}},
			event:  ceremonyEvt,
			match:  true,
		},
		{
			name:   "project-only filter matches all types",
			filter: EventFilter{ProjectID: strPtr("proj-1")},
			event:  storyEvt,
			match:  true,
		},
		{
			name:   "empty types with project matches all",
			filter: EventFilter{Types: []EventType{}, ProjectID: strPtr("proj-1")},
			event:  taskEvt,
			match:  true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			got := tt.filter.Matches(tt.event)
			if got != tt.match {
				t.Errorf("Matches() = %v, want %v", got, tt.match)
			}
		})
	}
}

// strPtr is a test helper that returns a pointer to the given string.
func strPtr(s string) *string {
	return &s
}
