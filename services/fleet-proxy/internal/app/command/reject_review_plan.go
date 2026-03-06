package command

import (
	"context"
	"errors"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

// RejectReviewPlanCmd carries the parameters for rejecting a story's review plan.
type RejectReviewPlanCmd struct {
	RequestID   string
	CeremonyID  string
	StoryID     string
	Reason      string
	RequestedBy string
}

// Validate checks that all required fields are present.
func (c RejectReviewPlanCmd) Validate() error {
	if c.RequestID == "" {
		return errors.New("request ID is required")
	}
	if c.CeremonyID == "" {
		return errors.New("ceremony ID is required")
	}
	if c.StoryID == "" {
		return errors.New("story ID is required")
	}
	if c.Reason == "" {
		return errors.New("rejection reason is required")
	}
	if c.RequestedBy == "" {
		return errors.New("requestedBy is required")
	}
	return nil
}

// RejectReviewPlanHandler orchestrates rejection of a story's review plan.
type RejectReviewPlanHandler struct {
	planning ports.PlanningClient
	audit    ports.AuditLogger
}

// NewRejectReviewPlanHandler wires the handler to its ports.
func NewRejectReviewPlanHandler(p ports.PlanningClient, a ports.AuditLogger) *RejectReviewPlanHandler {
	return &RejectReviewPlanHandler{planning: p, audit: a}
}

// Handle validates the command, delegates to the planning port, and records
// an audit event. It returns the updated backlog review result.
func (h *RejectReviewPlanHandler) Handle(ctx context.Context, cmd RejectReviewPlanCmd) (ports.BacklogReviewResult, error) {
	if err := cmd.Validate(); err != nil {
		h.recordAudit(ctx, cmd.RequestID, cmd.RequestedBy, false, err.Error())
		return ports.BacklogReviewResult{}, err
	}

	result, err := h.planning.RejectReviewPlan(ctx, cmd.CeremonyID, cmd.StoryID, cmd.RequestedBy, cmd.Reason)
	if err != nil {
		h.recordAudit(ctx, cmd.RequestID, cmd.RequestedBy, false, err.Error())
		return ports.BacklogReviewResult{}, err
	}

	h.recordAudit(ctx, cmd.RequestID, cmd.RequestedBy, true, "")
	return result, nil
}

func (h *RejectReviewPlanHandler) recordAudit(ctx context.Context, requestID, clientID string, success bool, errMsg string) {
	h.audit.Record(ctx, ports.AuditEvent{
		ClientID:  clientID,
		Method:    "RejectReviewPlan",
		RequestID: requestID,
		Timestamp: time.Now(),
		Success:   success,
		Error:     errMsg,
	})
}
