package command

import (
	"context"
	"errors"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

// CreateBacklogReviewCmd carries the parameters for creating a new backlog review ceremony.
type CreateBacklogReviewCmd struct {
	RequestID   string
	RequestedBy string
	StoryIDs    []string
}

// Validate checks that all required fields are present.
func (c CreateBacklogReviewCmd) Validate() error {
	if c.RequestID == "" {
		return errors.New("request ID is required")
	}
	if c.RequestedBy == "" {
		return errors.New("requestedBy is required")
	}
	return nil
}

// CreateBacklogReviewHandler orchestrates backlog review creation.
type CreateBacklogReviewHandler struct {
	planning ports.PlanningClient
	audit    ports.AuditLogger
}

// NewCreateBacklogReviewHandler wires the handler to its ports.
func NewCreateBacklogReviewHandler(p ports.PlanningClient, a ports.AuditLogger) *CreateBacklogReviewHandler {
	return &CreateBacklogReviewHandler{planning: p, audit: a}
}

// Handle validates the command, delegates to the planning port, and records
// an audit event. It returns the backlog review result.
func (h *CreateBacklogReviewHandler) Handle(ctx context.Context, cmd CreateBacklogReviewCmd) (ports.BacklogReviewResult, error) {
	if err := cmd.Validate(); err != nil {
		h.recordAudit(ctx, cmd.RequestID, cmd.RequestedBy, false, err.Error())
		return ports.BacklogReviewResult{}, err
	}

	result, err := h.planning.CreateBacklogReview(ctx, cmd.RequestedBy, cmd.StoryIDs)
	if err != nil {
		h.recordAudit(ctx, cmd.RequestID, cmd.RequestedBy, false, err.Error())
		return ports.BacklogReviewResult{}, err
	}

	h.recordAudit(ctx, cmd.RequestID, cmd.RequestedBy, true, "")
	return result, nil
}

func (h *CreateBacklogReviewHandler) recordAudit(ctx context.Context, requestID, clientID string, success bool, errMsg string) {
	h.audit.Record(ctx, ports.AuditEvent{
		ClientID:  clientID,
		Method:    "CreateBacklogReview",
		RequestID: requestID,
		Timestamp: time.Now(),
		Success:   success,
		Error:     errMsg,
	})
}
