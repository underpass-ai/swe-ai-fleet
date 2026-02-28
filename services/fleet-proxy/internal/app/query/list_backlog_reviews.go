package query

import (
	"context"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

// ListBacklogReviewsQuery carries the parameters for listing backlog review ceremonies.
type ListBacklogReviewsQuery struct {
	StatusFilter string
	Limit        int32
	Offset       int32
}

// ListBacklogReviewsResult wraps a page of backlog reviews with total count for pagination.
type ListBacklogReviewsResult struct {
	Reviews    []ports.BacklogReviewResult
	TotalCount int32
}

// ListBacklogReviewsHandler handles backlog review listing queries.
type ListBacklogReviewsHandler struct {
	planning ports.PlanningClient
}

// NewListBacklogReviewsHandler wires the handler to the planning port.
func NewListBacklogReviewsHandler(p ports.PlanningClient) *ListBacklogReviewsHandler {
	return &ListBacklogReviewsHandler{planning: p}
}

// Handle executes the query, applying default pagination if limits are not set.
func (h *ListBacklogReviewsHandler) Handle(ctx context.Context, q ListBacklogReviewsQuery) (ListBacklogReviewsResult, error) {
	limit := q.Limit
	if limit <= 0 {
		limit = 50
	}
	offset := max(q.Offset, 0)

	reviews, total, err := h.planning.ListBacklogReviews(ctx, q.StatusFilter, limit, offset)
	if err != nil {
		return ListBacklogReviewsResult{}, err
	}

	return ListBacklogReviewsResult{
		Reviews:    reviews,
		TotalCount: total,
	}, nil
}
