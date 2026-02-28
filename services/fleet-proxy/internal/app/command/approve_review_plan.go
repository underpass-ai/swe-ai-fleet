package command

import (
	"context"
	"errors"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

// ApproveReviewPlanCmd carries the parameters for approving a story's review plan.
type ApproveReviewPlanCmd struct {
	RequestID          string
	CeremonyID         string
	StoryID            string
	PONotes            string
	POConcerns         string
	PriorityAdjustment string
	POPriorityReason   string
	RequestedBy        string
}

// Validate checks that all required fields are present.
func (c ApproveReviewPlanCmd) Validate() error {
	if c.RequestID == "" {
		return errors.New("request ID is required")
	}
	if c.CeremonyID == "" {
		return errors.New("ceremony ID is required")
	}
	if c.StoryID == "" {
		return errors.New("story ID is required")
	}
	if c.PONotes == "" {
		return errors.New("PO notes are required")
	}
	if c.RequestedBy == "" {
		return errors.New("requestedBy is required")
	}
	return nil
}

// ApproveReviewPlanHandler orchestrates approval of a story's review plan.
type ApproveReviewPlanHandler struct {
	planning ports.PlanningClient
	audit    ports.AuditLogger
}

// NewApproveReviewPlanHandler wires the handler to its ports.
func NewApproveReviewPlanHandler(p ports.PlanningClient, a ports.AuditLogger) *ApproveReviewPlanHandler {
	return &ApproveReviewPlanHandler{planning: p, audit: a}
}

// Handle validates the command, delegates to the planning port, and records
// an audit event. It returns the updated backlog review result and the plan ID.
func (h *ApproveReviewPlanHandler) Handle(ctx context.Context, cmd ApproveReviewPlanCmd) (ports.BacklogReviewResult, string, error) {
	if err := cmd.Validate(); err != nil {
		h.recordAudit(ctx, cmd.RequestID, cmd.RequestedBy, false, err.Error())
		return ports.BacklogReviewResult{}, "", err
	}

	result, planID, err := h.planning.ApproveReviewPlan(ctx,
		cmd.CeremonyID, cmd.StoryID, cmd.RequestedBy,
		cmd.PONotes, cmd.POConcerns, cmd.PriorityAdjustment, cmd.POPriorityReason,
	)
	if err != nil {
		h.recordAudit(ctx, cmd.RequestID, cmd.RequestedBy, false, err.Error())
		return ports.BacklogReviewResult{}, "", err
	}

	h.recordAudit(ctx, cmd.RequestID, cmd.RequestedBy, true, "")
	return result, planID, nil
}

func (h *ApproveReviewPlanHandler) recordAudit(ctx context.Context, requestID, clientID string, success bool, errMsg string) {
	h.audit.Record(ctx, ports.AuditEvent{
		ClientID:  clientID,
		Method:    "ApproveReviewPlan",
		RequestID: requestID,
		Timestamp: time.Now(),
		Success:   success,
		Error:     errMsg,
	})
}
