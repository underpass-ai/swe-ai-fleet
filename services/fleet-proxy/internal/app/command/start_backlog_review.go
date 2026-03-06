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
	planning ports.PlanningClient
	audit    ports.AuditLogger
}

// NewStartBacklogReviewHandler wires the handler to its ports.
func NewStartBacklogReviewHandler(p ports.PlanningClient, a ports.AuditLogger) *StartBacklogReviewHandler {
	return &StartBacklogReviewHandler{planning: p, audit: a}
}

// Handle validates the command, delegates to the planning port, and records
// an audit event. It returns the backlog review result and the deliberation count.
func (h *StartBacklogReviewHandler) Handle(ctx context.Context, cmd StartBacklogReviewCmd) (ports.BacklogReviewResult, int32, error) {
	if err := cmd.Validate(); err != nil {
		h.recordAudit(ctx, cmd.RequestID, cmd.RequestedBy, false, err.Error())
		return ports.BacklogReviewResult{}, 0, err
	}

	result, count, err := h.planning.StartBacklogReview(ctx, cmd.CeremonyID, cmd.RequestedBy)
	if err != nil {
		h.recordAudit(ctx, cmd.RequestID, cmd.RequestedBy, false, err.Error())
		return ports.BacklogReviewResult{}, 0, err
	}

	h.recordAudit(ctx, cmd.RequestID, cmd.RequestedBy, true, "")
	return result, count, nil
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
