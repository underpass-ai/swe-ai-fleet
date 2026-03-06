package command

import (
	"context"
	"errors"
	"fmt"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// CreateBacklogReviewCmd carries the inputs for creating a backlog review ceremony.
type CreateBacklogReviewCmd struct {
	StoryIDs []string
}

// CreateBacklogReviewHandler orchestrates backlog review creation.
type CreateBacklogReviewHandler struct {
	client ports.FleetClient
}

// NewCreateBacklogReviewHandler returns a handler wired to the given FleetClient.
func NewCreateBacklogReviewHandler(client ports.FleetClient) *CreateBacklogReviewHandler {
	return &CreateBacklogReviewHandler{client: client}
}

// Handle validates the command, generates a request ID, and delegates to the fleet client.
func (h *CreateBacklogReviewHandler) Handle(ctx context.Context, cmd CreateBacklogReviewCmd) (domain.BacklogReview, error) {
	if len(cmd.StoryIDs) == 0 {
		return domain.BacklogReview{}, errors.New("create_backlog_review: at least one story_id is required")
	}

	requestID, err := generateRequestID()
	if err != nil {
		return domain.BacklogReview{}, fmt.Errorf("create_backlog_review: failed to generate request id: %w", err)
	}

	review, err := h.client.CreateBacklogReview(ctx, requestID, cmd.StoryIDs)
	if err != nil {
		return domain.BacklogReview{}, fmt.Errorf("create_backlog_review: %w", err)
	}

	return review, nil
}
