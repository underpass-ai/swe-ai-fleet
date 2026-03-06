package command

import (
	"context"
	"errors"
	"fmt"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// StartBacklogReviewCmd carries the inputs for starting a backlog review ceremony.
type StartBacklogReviewCmd struct {
	CeremonyID string
}

// StartBacklogReviewResult contains the outputs of starting a backlog review.
type StartBacklogReviewResult struct {
	Review domain.BacklogReview
	Total  int32
}

// StartBacklogReviewHandler orchestrates starting a backlog review.
type StartBacklogReviewHandler struct {
	client ports.FleetClient
}

// NewStartBacklogReviewHandler returns a handler wired to the given FleetClient.
func NewStartBacklogReviewHandler(client ports.FleetClient) *StartBacklogReviewHandler {
	return &StartBacklogReviewHandler{client: client}
}

// Handle validates the command, generates a request ID, and delegates to the fleet client.
func (h *StartBacklogReviewHandler) Handle(ctx context.Context, cmd StartBacklogReviewCmd) (StartBacklogReviewResult, error) {
	if cmd.CeremonyID == "" {
		return StartBacklogReviewResult{}, errors.New("start_backlog_review: ceremony_id is required")
	}

	requestID, err := generateRequestID()
	if err != nil {
		return StartBacklogReviewResult{}, fmt.Errorf("start_backlog_review: failed to generate request id: %w", err)
	}

	review, total, err := h.client.StartBacklogReview(ctx, requestID, cmd.CeremonyID)
	if err != nil {
		return StartBacklogReviewResult{}, fmt.Errorf("start_backlog_review: %w", err)
	}

	return StartBacklogReviewResult{Review: review, Total: total}, nil
}
