package query

import (
	"context"
	"errors"
	"fmt"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// GetBacklogReviewQuery carries the inputs for fetching a backlog review.
type GetBacklogReviewQuery struct {
	CeremonyID string
}

// GetBacklogReviewHandler fetches a single backlog review ceremony.
type GetBacklogReviewHandler struct {
	client ports.FleetClient
}

// NewGetBacklogReviewHandler returns a handler wired to the given FleetClient.
func NewGetBacklogReviewHandler(client ports.FleetClient) *GetBacklogReviewHandler {
	return &GetBacklogReviewHandler{client: client}
}

// Handle validates the query and delegates to the fleet client.
func (h *GetBacklogReviewHandler) Handle(ctx context.Context, q GetBacklogReviewQuery) (domain.BacklogReview, error) {
	if q.CeremonyID == "" {
		return domain.BacklogReview{}, errors.New("get_backlog_review: ceremony_id is required")
	}

	review, err := h.client.GetBacklogReview(ctx, q.CeremonyID)
	if err != nil {
		return domain.BacklogReview{}, fmt.Errorf("get_backlog_review: %w", err)
	}
	return review, nil
}
