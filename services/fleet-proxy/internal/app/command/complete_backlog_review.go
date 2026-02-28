package command

import (
	"context"
	"errors"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

// CompleteBacklogReviewCmd carries the parameters for completing a backlog review ceremony.
type CompleteBacklogReviewCmd struct {
	RequestID   string
	CeremonyID  string
	RequestedBy string
}

// Validate checks that all required fields are present.
func (c CompleteBacklogReviewCmd) Validate() error {
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

// CompleteBacklogReviewHandler orchestrates completion of a backlog review ceremony.
type CompleteBacklogReviewHandler struct {
	planning ports.PlanningClient
	audit    ports.AuditLogger
}

// NewCompleteBacklogReviewHandler wires the handler to its ports.
func NewCompleteBacklogReviewHandler(p ports.PlanningClient, a ports.AuditLogger) *CompleteBacklogReviewHandler {
	return &CompleteBacklogReviewHandler{planning: p, audit: a}
}

// Handle validates the command, delegates to the planning port, and records
// an audit event. It returns the updated backlog review result.
func (h *CompleteBacklogReviewHandler) Handle(ctx context.Context, cmd CompleteBacklogReviewCmd) (ports.BacklogReviewResult, error) {
	if err := cmd.Validate(); err != nil {
		h.recordAudit(ctx, cmd.RequestID, cmd.RequestedBy, false, err.Error())
		return ports.BacklogReviewResult{}, err
	}

	result, err := h.planning.CompleteBacklogReview(ctx, cmd.CeremonyID, cmd.RequestedBy)
	if err != nil {
		h.recordAudit(ctx, cmd.RequestID, cmd.RequestedBy, false, err.Error())
		return ports.BacklogReviewResult{}, err
	}

	h.recordAudit(ctx, cmd.RequestID, cmd.RequestedBy, true, "")
	return result, nil
}

func (h *CompleteBacklogReviewHandler) recordAudit(ctx context.Context, requestID, clientID string, success bool, errMsg string) {
	h.audit.Record(ctx, ports.AuditEvent{
		ClientID:  clientID,
		Method:    "CompleteBacklogReview",
		RequestID: requestID,
		Timestamp: time.Now(),
		Success:   success,
		Error:     errMsg,
	})
}
