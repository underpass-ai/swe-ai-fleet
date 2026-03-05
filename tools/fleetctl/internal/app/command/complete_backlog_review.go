package command

import (
	"context"
	"errors"
	"fmt"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// CompleteBacklogReviewCmd carries the inputs for completing a backlog review.
type CompleteBacklogReviewCmd struct {
	CeremonyID string
}

// CompleteBacklogReviewHandler orchestrates backlog review completion.
type CompleteBacklogReviewHandler struct {
	client ports.FleetClient
}

// NewCompleteBacklogReviewHandler returns a handler wired to the given FleetClient.
func NewCompleteBacklogReviewHandler(client ports.FleetClient) *CompleteBacklogReviewHandler {
	return &CompleteBacklogReviewHandler{client: client}
}

// Handle validates the command, generates a request ID, and delegates to the fleet client.
func (h *CompleteBacklogReviewHandler) Handle(ctx context.Context, cmd CompleteBacklogReviewCmd) (domain.BacklogReview, error) {
	if cmd.CeremonyID == "" {
		return domain.BacklogReview{}, errors.New("complete_backlog_review: ceremony_id is required")
	}

	requestID, err := generateRequestID()
	if err != nil {
		return domain.BacklogReview{}, fmt.Errorf("complete_backlog_review: failed to generate request id: %w", err)
	}

	review, err := h.client.CompleteBacklogReview(ctx, requestID, cmd.CeremonyID)
	if err != nil {
		return domain.BacklogReview{}, fmt.Errorf("complete_backlog_review: %w", err)
	}

	return review, nil
}
