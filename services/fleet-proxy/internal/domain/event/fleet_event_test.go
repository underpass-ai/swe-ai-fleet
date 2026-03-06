package event

import (
	"strings"
	"testing"
	"time"
)

func TestNewFleetEvent(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name           string
		eventType      EventType
		idempotencyKey string
		correlationID  string
		producer       string
		payload        []byte
		wantErr        bool
		errSubstr      string
	}{
		{
			name:           "valid event with payload",
			eventType:      EventStoryCreated,
			idempotencyKey: "idem-123",
			correlationID:  "corr-456",
			producer:       "fleet-proxy",
			payload:        []byte(`{"storyId":"s-1"}`),
		},
		{
			name:           "valid event without payload",
			eventType:      EventCeremonyStarted,
			idempotencyKey: "idem-789",
			correlationID:  "corr-012",
			producer:       "ceremony-service",
			payload:        nil,
		},
		{
			name:           "invalid event type",
			eventType:      EventType("nonexistent.type"),
			idempotencyKey: "idem-1",
			correlationID:  "corr-1",
			producer:       "test",
			wantErr:        true,
			errSubstr:      "invalid event type",
		},
		{
			name:           "empty event type",
			eventType:      EventType(""),
			idempotencyKey: "idem-1",
			correlationID:  "corr-1",
			producer:       "test",
			wantErr:        true,
			errSubstr:      "invalid event type",
		},
		{
			name:           "empty idempotency key",
			eventType:      EventStoryCreated,
			idempotencyKey: "",
			correlationID:  "corr-1",
			producer:       "test",
			wantErr:        true,
			errSubstr:      "idempotency key cannot be empty",
		},
		{
			name:           "empty correlation ID",
			eventType:      EventStoryCreated,
			idempotencyKey: "idem-1",
			correlationID:  "",
			producer:       "test",
			wantErr:        true,
			errSubstr:      "correlation ID cannot be empty",
		},
		{
			name:           "empty producer",
			eventType:      EventStoryCreated,
			idempotencyKey: "idem-1",
			correlationID:  "corr-1",
			producer:       "",
			wantErr:        true,
			errSubstr:      "producer cannot be empty",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			before := time.Now()
			evt, err := NewFleetEvent(tt.eventType, tt.idempotencyKey, tt.correlationID, tt.producer, tt.payload)
			after := time.Now()

			if tt.wantErr {
				if err == nil {
					t.Fatalf("NewFleetEvent() expected error containing %q, got nil", tt.errSubstr)
				}
				if !strings.Contains(err.Error(), tt.errSubstr) {
					t.Fatalf("NewFleetEvent() error = %q, want substring %q", err.Error(), tt.errSubstr)
				}
				return
			}

			if err != nil {
				t.Fatalf("NewFleetEvent() unexpected error: %v", err)
			}

			if evt.Type != tt.eventType {
				t.Errorf("Type = %q, want %q", evt.Type, tt.eventType)
			}
			if evt.IdempotencyKey != tt.idempotencyKey {
				t.Errorf("IdempotencyKey = %q, want %q", evt.IdempotencyKey, tt.idempotencyKey)
			}
			if evt.CorrelationID != tt.correlationID {
				t.Errorf("CorrelationID = %q, want %q", evt.CorrelationID, tt.correlationID)
			}
			if evt.Producer != tt.producer {
				t.Errorf("Producer = %q, want %q", evt.Producer, tt.producer)
			}
			if string(evt.Payload) != string(tt.payload) {
				t.Errorf("Payload = %q, want %q", evt.Payload, tt.payload)
			}

			// Verify timestamp is set to approximately now.
			if evt.Timestamp.Before(before) || evt.Timestamp.After(after) {
				t.Errorf("Timestamp = %v, want between %v and %v", evt.Timestamp, before, after)
			}
		})
	}
}

func TestNewFleetEvent_AllValidTypes(t *testing.T) {
	t.Parallel()

	allTypes := []EventType{
		EventStoryCreated,
		EventStoryTransitioned,
		EventTaskCreated,
		EventCeremonyStarted,
		EventCeremonyCompleted,
		EventDeliberationReceived,
	}

	for _, et := range allTypes {
		t.Run(string(et), func(t *testing.T) {
			t.Parallel()

			evt, err := NewFleetEvent(et, "idem-key", "corr-id", "producer", nil)
			if err != nil {
				t.Fatalf("NewFleetEvent(%q) unexpected error: %v", et, err)
			}
			if evt.Type != et {
				t.Errorf("Type = %q, want %q", evt.Type, et)
			}
		})
	}
}
