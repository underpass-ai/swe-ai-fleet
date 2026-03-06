package ports

import (
	"context"
	"time"
)

// AuditLogger is a port for recording audit trail entries.
// Every command and query processed by the application layer should produce
// an audit event regardless of success or failure.
type AuditLogger interface {
	// Record persists an audit event. Implementations must not block the
	// caller; they may buffer and flush asynchronously.
	Record(ctx context.Context, evt AuditEvent)
}

// AuditEvent captures the metadata of a single auditable operation.
type AuditEvent struct {
	// ClientID identifies the authenticated caller (SPIFFE URI).
	ClientID string

	// Method is the RPC or operation name (e.g., "CreateProject").
	Method string

	// RequestID is the idempotency/correlation key for this request.
	RequestID string

	// Timestamp is when the operation was processed.
	Timestamp time.Time

	// Success indicates whether the operation completed without error.
	Success bool

	// Error holds the error message if the operation failed.
	Error string
}
