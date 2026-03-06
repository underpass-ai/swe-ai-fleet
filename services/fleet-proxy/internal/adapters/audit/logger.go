// Package audit provides a structured logging adapter implementing
// ports.AuditLogger. It writes audit events using the standard library's
// slog package.
package audit

import (
	"context"
	"log/slog"
	"os"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

// Logger implements ports.AuditLogger using structured slog output.
type Logger struct {
	logger *slog.Logger
}

// NewLogger creates a Logger that writes JSON-formatted audit events to stdout.
func NewLogger() *Logger {
	return &Logger{
		logger: slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
			Level: slog.LevelInfo,
		})),
	}
}

// NewLoggerWithHandler creates a Logger with a custom slog handler.
// This is useful for testing or routing audit logs to a different sink.
func NewLoggerWithHandler(h slog.Handler) *Logger {
	return &Logger{
		logger: slog.New(h),
	}
}

// Record persists an audit event as a structured log entry.
func (l *Logger) Record(_ context.Context, evt ports.AuditEvent) {
	attrs := []slog.Attr{
		slog.String("client_id", evt.ClientID),
		slog.String("method", evt.Method),
		slog.String("request_id", evt.RequestID),
		slog.Time("timestamp", evt.Timestamp),
		slog.Bool("success", evt.Success),
	}

	if evt.Error != "" {
		attrs = append(attrs, slog.String("error", evt.Error))
	}

	// Convert []slog.Attr to []any for LogAttrs.
	l.logger.LogAttrs(context.Background(), slog.LevelInfo, "audit",
		attrs...,
	)
}
