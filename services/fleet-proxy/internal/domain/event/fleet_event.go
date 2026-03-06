package event

import (
	"errors"
	"time"
)

// FleetEvent is a value object representing a domain event produced within the
// swe-ai-fleet system. Events are immutable once created and carry all the
// metadata needed for reliable delivery, deduplication, and correlation.
type FleetEvent struct {
	// Type classifies the event.
	Type EventType

	// IdempotencyKey is a unique key used for deduplication. Consumers must
	// treat events with the same idempotency key as duplicates.
	IdempotencyKey string

	// CorrelationID links this event to a broader workflow or saga.
	CorrelationID string

	// Timestamp is when the event was produced.
	Timestamp time.Time

	// Producer identifies the service or agent that produced this event.
	Producer string

	// Payload is the serialized event-specific data (typically JSON or protobuf).
	Payload []byte
}

// NewFleetEvent creates a validated FleetEvent.
// It requires a valid event type, non-empty idempotency key, correlation ID,
// and producer.
func NewFleetEvent(
	eventType EventType,
	idempotencyKey string,
	correlationID string,
	producer string,
	payload []byte,
) (FleetEvent, error) {
	if !eventType.IsValid() {
		return FleetEvent{}, errors.New("invalid event type")
	}

	if idempotencyKey == "" {
		return FleetEvent{}, errors.New("idempotency key cannot be empty")
	}

	if correlationID == "" {
		return FleetEvent{}, errors.New("correlation ID cannot be empty")
	}

	if producer == "" {
		return FleetEvent{}, errors.New("producer cannot be empty")
	}

	return FleetEvent{
		Type:           eventType,
		IdempotencyKey: idempotencyKey,
		CorrelationID:  correlationID,
		Timestamp:      time.Now(),
		Producer:       producer,
		Payload:        payload,
	}, nil
}
