package store

import (
	"context"
	"time"
)

type DeliberationStatus string

const (
	DeliberationStatusRunning   DeliberationStatus = "running"
	DeliberationStatusCompleted DeliberationStatus = "completed"
	DeliberationStatusFailed    DeliberationStatus = "failed"
)

// DeliberationRecord represents persisted tracking state for a deliberation.
// It is intentionally minimal and transport-agnostic.
type DeliberationRecord struct {
	DeliberationID string             `json:"deliberation_id"`
	TaskID         string             `json:"task_id"`
	Status         DeliberationStatus `json:"status"`
	CreatedAtUTC   time.Time          `json:"created_at_utc"`
	UpdatedAtUTC   time.Time          `json:"updated_at_utc"`
	// Metadata is reserved for correlation fields (story_id, plan_id, etc.).
	Metadata map[string]string `json:"metadata,omitempty"`
}

// DeliberationStore is a durable tracking store.
//
// Required behavior:
// - Get must work across process restarts.
// - Records expire automatically via TTL.
// - Active index should not leak indefinitely.
type DeliberationStore interface {
	Upsert(ctx context.Context, record DeliberationRecord, ttl time.Duration) error
	Get(ctx context.Context, deliberationID string) (DeliberationRecord, bool, error)
	Touch(ctx context.Context, deliberationID string, ttl time.Duration, updatedAtUTC time.Time) error
	MarkCompleted(ctx context.Context, deliberationID string, updatedAtUTC time.Time) error
	MarkFailed(ctx context.Context, deliberationID string, updatedAtUTC time.Time) error
	ListActive(ctx context.Context, limit int) ([]DeliberationRecord, error)
}
