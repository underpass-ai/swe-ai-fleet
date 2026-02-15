package audit

import (
	"context"
	"log/slog"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
)

type LoggerAudit struct {
	logger *slog.Logger
}

func NewLoggerAudit(logger *slog.Logger) *LoggerAudit {
	return &LoggerAudit{logger: logger}
}

func (a *LoggerAudit) Record(_ context.Context, event app.AuditEvent) {
	a.logger.Info("audit.tool_invocation",
		"at", event.At,
		"session_id", event.SessionID,
		"tool", event.ToolName,
		"invocation_id", event.InvocationID,
		"correlation_id", event.CorrelationID,
		"status", event.Status,
		"actor_id", event.ActorID,
		"tenant_id", event.TenantID,
		"metadata", event.Metadata,
	)
}
