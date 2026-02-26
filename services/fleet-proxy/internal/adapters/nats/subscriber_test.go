package nats

import (
	"encoding/json"
	"strings"
	"testing"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/event"
)

// --- DecodeWireEvent tests ---

func TestDecodeWireEvent_ValidEvent(t *testing.T) {
	t.Parallel()

	ts := time.Date(2026, 2, 25, 12, 0, 0, 0, time.UTC)

	raw, err := json.Marshal(wireEvent{
		Type:           "story.created",
		IdempotencyKey: "key-1",
		CorrelationID:  "corr-1",
		Timestamp:      ts,
		Producer:       "planning-service",
		ProjectID:      "proj-42",
		Payload:        json.RawMessage(`{"title":"Build login page"}`),
	})
	if err != nil {
		t.Fatalf("marshal wire event: %v", err)
	}

	evt, err := DecodeWireEvent(raw)
	if err != nil {
		t.Fatalf("DecodeWireEvent() unexpected error: %v", err)
	}

	if evt.Type != event.EventStoryCreated {
		t.Errorf("Type = %q, want %q", evt.Type, event.EventStoryCreated)
	}
	if evt.IdempotencyKey != "key-1" {
		t.Errorf("IdempotencyKey = %q, want %q", evt.IdempotencyKey, "key-1")
	}
	if evt.CorrelationID != "corr-1" {
		t.Errorf("CorrelationID = %q, want %q", evt.CorrelationID, "corr-1")
	}
	if !evt.Timestamp.Equal(ts) {
		t.Errorf("Timestamp = %v, want %v", evt.Timestamp, ts)
	}
	if evt.Producer != "planning-service" {
		t.Errorf("Producer = %q, want %q", evt.Producer, "planning-service")
	}
	if string(evt.Payload) != `{"title":"Build login page"}` {
		t.Errorf("Payload = %q, want %q", string(evt.Payload), `{"title":"Build login page"}`)
	}
}

func TestDecodeWireEvent_AllEventTypes(t *testing.T) {
	t.Parallel()

	types := []struct {
		wire     string
		expected event.EventType
	}{
		{"story.created", event.EventStoryCreated},
		{"story.transitioned", event.EventStoryTransitioned},
		{"task.created", event.EventTaskCreated},
		{"ceremony.started", event.EventCeremonyStarted},
		{"ceremony.completed", event.EventCeremonyCompleted},
		{"deliberation.received", event.EventDeliberationReceived},
	}

	for _, tt := range types {
		t.Run(tt.wire, func(t *testing.T) {
			t.Parallel()

			raw, _ := json.Marshal(wireEvent{
				Type:           tt.wire,
				IdempotencyKey: "k",
				CorrelationID:  "c",
				Timestamp:      time.Now(),
				Producer:       "p",
			})

			evt, err := DecodeWireEvent(raw)
			if err != nil {
				t.Fatalf("DecodeWireEvent(%q) unexpected error: %v", tt.wire, err)
			}
			if evt.Type != tt.expected {
				t.Errorf("Type = %q, want %q", evt.Type, tt.expected)
			}
		})
	}
}

func TestDecodeWireEvent_UnknownType(t *testing.T) {
	t.Parallel()

	raw, _ := json.Marshal(wireEvent{
		Type:           "story.deleted",
		IdempotencyKey: "k",
		CorrelationID:  "c",
		Timestamp:      time.Now(),
		Producer:       "p",
	})

	_, err := DecodeWireEvent(raw)
	if err == nil {
		t.Fatal("DecodeWireEvent() expected error for unknown type, got nil")
	}
	if !strings.Contains(err.Error(), "unknown type") {
		t.Errorf("error = %q, want substring %q", err.Error(), "unknown type")
	}
}

func TestDecodeWireEvent_InvalidJSON(t *testing.T) {
	t.Parallel()

	_, err := DecodeWireEvent([]byte(`{not json`))
	if err == nil {
		t.Fatal("DecodeWireEvent() expected error for invalid JSON, got nil")
	}
	if !strings.Contains(err.Error(), "decode wire event") {
		t.Errorf("error = %q, want substring %q", err.Error(), "decode wire event")
	}
}

func TestDecodeWireEvent_EmptyPayload(t *testing.T) {
	t.Parallel()

	raw, _ := json.Marshal(wireEvent{
		Type:           "task.created",
		IdempotencyKey: "k",
		CorrelationID:  "c",
		Timestamp:      time.Now(),
		Producer:       "p",
	})

	evt, err := DecodeWireEvent(raw)
	if err != nil {
		t.Fatalf("DecodeWireEvent() unexpected error: %v", err)
	}
	if evt.Payload != nil {
		t.Errorf("Payload = %q, want nil", string(evt.Payload))
	}
}

// --- buildSubjectFilters tests ---

func TestBuildSubjectFilters_TypesOnly(t *testing.T) {
	t.Parallel()

	f := event.EventFilter{
		Types: []event.EventType{event.EventStoryCreated, event.EventTaskCreated},
	}

	got := buildSubjectFilters(f)

	want := []string{
		"fleet.events.story-created",
		"fleet.events.task-created",
	}

	if len(got) != len(want) {
		t.Fatalf("buildSubjectFilters() returned %d subjects, want %d", len(got), len(want))
	}
	for i, s := range got {
		if s != want[i] {
			t.Errorf("subject[%d] = %q, want %q", i, s, want[i])
		}
	}
}

func TestBuildSubjectFilters_ProjectOnly(t *testing.T) {
	t.Parallel()

	pid := "proj-42"
	f := event.EventFilter{
		ProjectID: &pid,
	}

	got := buildSubjectFilters(f)

	if len(got) != 1 {
		t.Fatalf("buildSubjectFilters() returned %d subjects, want 1", len(got))
	}
	want := "fleet.events.*.project.proj-42"
	if got[0] != want {
		t.Errorf("subject = %q, want %q", got[0], want)
	}
}

func TestBuildSubjectFilters_TypesAndProject(t *testing.T) {
	t.Parallel()

	pid := "proj-99"
	f := event.EventFilter{
		Types:     []event.EventType{event.EventCeremonyStarted, event.EventCeremonyCompleted},
		ProjectID: &pid,
	}

	got := buildSubjectFilters(f)

	want := []string{
		"fleet.events.ceremony-started.project.proj-99",
		"fleet.events.ceremony-completed.project.proj-99",
	}

	if len(got) != len(want) {
		t.Fatalf("buildSubjectFilters() returned %d subjects, want %d", len(got), len(want))
	}
	for i, s := range got {
		if s != want[i] {
			t.Errorf("subject[%d] = %q, want %q", i, s, want[i])
		}
	}
}

func TestBuildSubjectFilters_Wildcard(t *testing.T) {
	t.Parallel()

	// This case should not normally happen because EventFilter validates
	// that at least one criterion is set. But the function should still
	// produce a safe wildcard.
	f := event.EventFilter{}

	got := buildSubjectFilters(f)

	if len(got) != 1 {
		t.Fatalf("buildSubjectFilters() returned %d subjects, want 1", len(got))
	}
	if got[0] != "fleet.events.>" {
		t.Errorf("subject = %q, want %q", got[0], "fleet.events.>")
	}
}

// --- typeToSubjectSegment tests ---

func TestTypeToSubjectSegment(t *testing.T) {
	t.Parallel()

	tests := []struct {
		input event.EventType
		want  string
	}{
		{event.EventStoryCreated, "story-created"},
		{event.EventStoryTransitioned, "story-transitioned"},
		{event.EventTaskCreated, "task-created"},
		{event.EventCeremonyStarted, "ceremony-started"},
		{event.EventCeremonyCompleted, "ceremony-completed"},
		{event.EventDeliberationReceived, "deliberation-received"},
	}

	for _, tt := range tests {
		t.Run(string(tt.input), func(t *testing.T) {
			t.Parallel()

			got := typeToSubjectSegment(tt.input)
			if got != tt.want {
				t.Errorf("typeToSubjectSegment(%q) = %q, want %q", tt.input, got, tt.want)
			}
		})
	}
}

// --- Lazy subscriber tests ---

func TestNewLazySubscriber_DoesNotConnect(t *testing.T) {
	t.Parallel()

	// NewLazySubscriber should never attempt a connection to the given URL.
	// If it did, this would fail because the URL is unreachable.
	s := NewLazySubscriber("nats://unreachable-host:4222")
	if s == nil {
		t.Fatal("NewLazySubscriber() returned nil")
	}
	if s.nc != nil {
		t.Error("NewLazySubscriber() should not have an active NATS connection")
	}
	if s.js != nil {
		t.Error("NewLazySubscriber() should not have a JetStream context")
	}
	if s.url != "nats://unreachable-host:4222" {
		t.Errorf("url = %q, want %q", s.url, "nats://unreachable-host:4222")
	}
}

func TestClose_Idempotent(t *testing.T) {
	t.Parallel()

	s := NewLazySubscriber("nats://localhost:4222")

	// First close should succeed.
	if err := s.Close(); err != nil {
		t.Fatalf("first Close() error: %v", err)
	}

	// Second close should also succeed (idempotent).
	if err := s.Close(); err != nil {
		t.Fatalf("second Close() error: %v", err)
	}
}

func TestEnsureConnected_AfterClose(t *testing.T) {
	t.Parallel()

	s := NewLazySubscriber("nats://localhost:4222")
	_ = s.Close()

	err := s.ensureConnected()
	if err == nil {
		t.Fatal("ensureConnected() expected error after Close, got nil")
	}
	if !strings.Contains(err.Error(), "already closed") {
		t.Errorf("error = %q, want substring %q", err.Error(), "already closed")
	}
}
