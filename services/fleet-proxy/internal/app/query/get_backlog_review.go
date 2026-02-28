package query

import (
	"context"
	"errors"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

// GetBacklogReviewQuery carries the parameters for fetching a single backlog review ceremony.
type GetBacklogReviewQuery struct {
	CeremonyID string
}

// GetBacklogReviewHandler handles backlog review fetch queries.
type GetBacklogReviewHandler struct {
	planning ports.PlanningClient
}

// NewGetBacklogReviewHandler wires the handler to the planning port.
func NewGetBacklogReviewHandler(p ports.PlanningClient) *GetBacklogReviewHandler {
	return &GetBacklogReviewHandler{planning: p}
}

// Handle validates the query and delegates to the planning port.
func (h *GetBacklogReviewHandler) Handle(ctx context.Context, q GetBacklogReviewQuery) (ports.BacklogReviewResult, error) {
	if q.CeremonyID == "" {
		return ports.BacklogReviewResult{}, errors.New("ceremony ID is required")
	}
	return h.planning.GetBacklogReview(ctx, q.CeremonyID)
}
