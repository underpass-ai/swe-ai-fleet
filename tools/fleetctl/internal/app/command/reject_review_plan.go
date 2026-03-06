package command

import (
	"context"
	"errors"
	"fmt"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// RejectReviewPlanCmd carries the inputs for rejecting a story's review plan.
type RejectReviewPlanCmd struct {
	CeremonyID string
	StoryID    string
	Reason     string
}

// RejectReviewPlanHandler orchestrates review plan rejection.
type RejectReviewPlanHandler struct {
	client ports.FleetClient
}

// NewRejectReviewPlanHandler returns a handler wired to the given FleetClient.
func NewRejectReviewPlanHandler(client ports.FleetClient) *RejectReviewPlanHandler {
	return &RejectReviewPlanHandler{client: client}
}

// Handle validates the command, generates a request ID, and delegates to the fleet client.
func (h *RejectReviewPlanHandler) Handle(ctx context.Context, cmd RejectReviewPlanCmd) (domain.BacklogReview, error) {
	if cmd.CeremonyID == "" {
		return domain.BacklogReview{}, errors.New("reject_review_plan: ceremony_id is required")
	}
	if cmd.StoryID == "" {
		return domain.BacklogReview{}, errors.New("reject_review_plan: story_id is required")
	}
	if cmd.Reason == "" {
		return domain.BacklogReview{}, errors.New("reject_review_plan: reason is required")
	}

	requestID, err := generateRequestID()
	if err != nil {
		return domain.BacklogReview{}, fmt.Errorf("reject_review_plan: failed to generate request id: %w", err)
	}

	review, err := h.client.RejectReviewPlan(ctx, requestID, cmd.CeremonyID, cmd.StoryID, cmd.Reason)
	if err != nil {
		return domain.BacklogReview{}, fmt.Errorf("reject_review_plan: %w", err)
	}

	return review, nil
}
