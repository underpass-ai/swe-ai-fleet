package query

import (
	"context"
	"fmt"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// ListBacklogReviewsHandler returns backlog review ceremonies with optional filtering.
type ListBacklogReviewsHandler struct {
	client ports.FleetClient
}

// NewListBacklogReviewsHandler returns a handler wired to the given FleetClient.
func NewListBacklogReviewsHandler(client ports.FleetClient) *ListBacklogReviewsHandler {
	return &ListBacklogReviewsHandler{client: client}
}

// Handle delegates to the fleet client and returns the matching reviews and total count.
func (h *ListBacklogReviewsHandler) Handle(ctx context.Context, statusFilter string, limit, offset int32) ([]domain.BacklogReview, int32, error) {
	reviews, total, err := h.client.ListBacklogReviews(ctx, statusFilter, limit, offset)
	if err != nil {
		return nil, 0, fmt.Errorf("list_backlog_reviews: %w", err)
	}
	return reviews, total, nil
}
