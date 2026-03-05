package command

import (
	"context"
	"errors"
	"fmt"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// CancelBacklogReviewCmd carries the inputs for cancelling a backlog review.
type CancelBacklogReviewCmd struct {
	CeremonyID string
}

// CancelBacklogReviewHandler orchestrates backlog review cancellation.
type CancelBacklogReviewHandler struct {
	client ports.FleetClient
}

// NewCancelBacklogReviewHandler returns a handler wired to the given FleetClient.
func NewCancelBacklogReviewHandler(client ports.FleetClient) *CancelBacklogReviewHandler {
	return &CancelBacklogReviewHandler{client: client}
}

// Handle validates the command, generates a request ID, and delegates to the fleet client.
func (h *CancelBacklogReviewHandler) Handle(ctx context.Context, cmd CancelBacklogReviewCmd) (domain.BacklogReview, error) {
	if cmd.CeremonyID == "" {
		return domain.BacklogReview{}, errors.New("cancel_backlog_review: ceremony_id is required")
	}

	requestID, err := generateRequestID()
	if err != nil {
		return domain.BacklogReview{}, fmt.Errorf("cancel_backlog_review: failed to generate request id: %w", err)
	}

	review, err := h.client.CancelBacklogReview(ctx, requestID, cmd.CeremonyID)
	if err != nil {
		return domain.BacklogReview{}, fmt.Errorf("cancel_backlog_review: %w", err)
	}

	return review, nil
}
