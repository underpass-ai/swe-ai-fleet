package domain

import "fmt"

// FleetEvent represents a single event received from the fleet control
// plane event stream. Payload is kept as raw bytes so the TUI can
// decide how to render it (table, JSON, etc.).
type FleetEvent struct {
	Type           string
	IdempotencyKey string
	CorrelationID  string
	Timestamp      string
	Producer       string
	Payload        []byte
}

// Summary returns a human-readable one-liner suitable for log output or
// the TUI event stream. The format varies by event type to surface the
// most relevant information at a glance.
func (e FleetEvent) Summary() string {
	switch e.Type {
	case "story.created":
		return fmt.Sprintf("[%s] story created by %s (key=%s)", e.Timestamp, e.Producer, e.IdempotencyKey)
	case "story.transitioned":
		return fmt.Sprintf("[%s] story transitioned (corr=%s)", e.Timestamp, e.CorrelationID)
	case "task.assigned":
		return fmt.Sprintf("[%s] task assigned by %s (corr=%s)", e.Timestamp, e.Producer, e.CorrelationID)
	case "task.completed":
		return fmt.Sprintf("[%s] task completed (corr=%s)", e.Timestamp, e.CorrelationID)
	case "ceremony.started":
		return fmt.Sprintf("[%s] ceremony started by %s (corr=%s)", e.Timestamp, e.Producer, e.CorrelationID)
	case "ceremony.step_completed":
		return fmt.Sprintf("[%s] ceremony step completed (corr=%s)", e.Timestamp, e.CorrelationID)
	case "ceremony.completed":
		return fmt.Sprintf("[%s] ceremony completed (corr=%s)", e.Timestamp, e.CorrelationID)
	case "project.created":
		return fmt.Sprintf("[%s] project created by %s (key=%s)", e.Timestamp, e.Producer, e.IdempotencyKey)
	default:
		return fmt.Sprintf("[%s] %s from %s (corr=%s)", e.Timestamp, e.Type, e.Producer, e.CorrelationID)
	}
}
