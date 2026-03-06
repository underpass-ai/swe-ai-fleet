package command

import (
	"context"
	"errors"
	"fmt"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// ApproveReviewPlanCmd carries the inputs for approving a story's review plan.
type ApproveReviewPlanCmd struct {
	CeremonyID  string
	StoryID     string
	PONotes     string
	POConcerns  string
	PriorityAdj string
	PrioReason  string
}

// ApproveReviewPlanResult contains the outputs of approving a review plan.
type ApproveReviewPlanResult struct {
	Review domain.BacklogReview
	PlanID string
}

// ApproveReviewPlanHandler orchestrates review plan approval.
type ApproveReviewPlanHandler struct {
	client ports.FleetClient
}

// NewApproveReviewPlanHandler returns a handler wired to the given FleetClient.
func NewApproveReviewPlanHandler(client ports.FleetClient) *ApproveReviewPlanHandler {
	return &ApproveReviewPlanHandler{client: client}
}

// Handle validates the command, generates a request ID, and delegates to the fleet client.
func (h *ApproveReviewPlanHandler) Handle(ctx context.Context, cmd ApproveReviewPlanCmd) (ApproveReviewPlanResult, error) {
	if cmd.CeremonyID == "" {
		return ApproveReviewPlanResult{}, errors.New("approve_review_plan: ceremony_id is required")
	}
	if cmd.StoryID == "" {
		return ApproveReviewPlanResult{}, errors.New("approve_review_plan: story_id is required")
	}
	if cmd.PONotes == "" {
		return ApproveReviewPlanResult{}, errors.New("approve_review_plan: po_notes is required")
	}

	requestID, err := generateRequestID()
	if err != nil {
		return ApproveReviewPlanResult{}, fmt.Errorf("approve_review_plan: failed to generate request id: %w", err)
	}

	review, planID, err := h.client.ApproveReviewPlan(ctx, ports.ApproveReviewPlanInput{
		RequestID:   requestID,
		CeremonyID:  cmd.CeremonyID,
		StoryID:     cmd.StoryID,
		PONotes:     cmd.PONotes,
		POConcerns:  cmd.POConcerns,
		PriorityAdj: cmd.PriorityAdj,
		PrioReason:  cmd.PrioReason,
	})
	if err != nil {
		return ApproveReviewPlanResult{}, fmt.Errorf("approve_review_plan: %w", err)
	}

	return ApproveReviewPlanResult{Review: review, PlanID: planID}, nil
}
