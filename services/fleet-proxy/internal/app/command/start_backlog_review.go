package command

import (
	"context"
	"errors"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

// StartBacklogReviewCmd carries the parameters for starting a backlog review.
type StartBacklogReviewCmd struct {
	RequestID   string
	CeremonyID  string
	RequestedBy string
}

// Validate checks that all required fields are present.
func (c StartBacklogReviewCmd) Validate() error {
	if c.RequestID == "" {
		return errors.New("request ID is required")
	}
	if c.CeremonyID == "" {
		return errors.New("ceremony ID is required")
	}
	if c.RequestedBy == "" {
		return errors.New("requestedBy is required")
	}
	return nil
}

// StartBacklogReviewHandler orchestrates starting a backlog review ceremony.
type StartBacklogReviewHandler struct {
	ceremony ports.CeremonyClient
	audit    ports.AuditLogger
}

// NewStartBacklogReviewHandler wires the handler to its ports.
func NewStartBacklogReviewHandler(c ports.CeremonyClient, a ports.AuditLogger) *StartBacklogReviewHandler {
	return &StartBacklogReviewHandler{ceremony: c, audit: a}
}

// Handle validates the command, delegates to the ceremony port, and records
// an audit event. It returns the review count.
func (h *StartBacklogReviewHandler) Handle(ctx context.Context, cmd StartBacklogReviewCmd) (int32, error) {
	if err := cmd.Validate(); err != nil {
		h.recordAudit(ctx, cmd.RequestID, cmd.RequestedBy, false, err.Error())
		return 0, err
	}

	reviewCount, err := h.ceremony.StartBacklogReview(ctx, cmd.CeremonyID)
	if err != nil {
		h.recordAudit(ctx, cmd.RequestID, cmd.RequestedBy, false, err.Error())
		return 0, err
	}

	h.recordAudit(ctx, cmd.RequestID, cmd.RequestedBy, true, "")
	return reviewCount, nil
}

func (h *StartBacklogReviewHandler) recordAudit(ctx context.Context, requestID, clientID string, success bool, errMsg string) {
	h.audit.Record(ctx, ports.AuditEvent{
		ClientID:  clientID,
		Method:    "StartBacklogReview",
		RequestID: requestID,
		Timestamp: time.Now(),
		Success:   success,
		Error:     errMsg,
	})
}
