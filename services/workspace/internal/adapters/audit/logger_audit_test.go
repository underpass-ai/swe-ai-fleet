package audit

import (
	"bytes"
	"context"
	"encoding/json"
	"log/slog"
	"testing"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
)

func TestLoggerAuditRecord(t *testing.T) {
	buffer := &bytes.Buffer{}
	logger := slog.New(slog.NewJSONHandler(buffer, nil))
	a := NewLoggerAudit(logger)

	a.Record(context.Background(), app.AuditEvent{
		At:            time.Now().UTC(),
		SessionID:     "session-1",
		ToolName:      "fs.read",
		InvocationID:  "inv-1",
		CorrelationID: "corr-1",
		Status:        "succeeded",
		ActorID:       "alice",
		TenantID:      "tenant-a",
		Metadata:      map[string]string{"k": "v"},
	})

	if buffer.Len() == 0 {
		t.Fatal("expected log output")
	}

	var payload map[string]any
	if err := json.Unmarshal(buffer.Bytes(), &payload); err != nil {
		t.Fatalf("unexpected json log format: %v", err)
	}
	if payload["msg"] != "audit.tool_invocation" {
		t.Fatalf("unexpected log message: %#v", payload)
	}
}
