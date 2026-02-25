package query

import (
	"context"
	"errors"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

// ListStoriesQuery carries the parameters for listing stories.
type ListStoriesQuery struct {
	EpicID      string
	StateFilter string
	Limit       int32
	Offset      int32
}

// ListStoriesResult wraps a page of stories with total count for pagination.
type ListStoriesResult struct {
	Stories    []ports.StoryResult
	TotalCount int32
}

// ListStoriesHandler handles story listing queries.
type ListStoriesHandler struct {
	planning ports.PlanningClient
}

// NewListStoriesHandler wires the handler to the planning port.
func NewListStoriesHandler(p ports.PlanningClient) *ListStoriesHandler {
	return &ListStoriesHandler{planning: p}
}

// Handle validates the query and delegates to the planning port.
func (h *ListStoriesHandler) Handle(ctx context.Context, q ListStoriesQuery) (ListStoriesResult, error) {
	if q.EpicID == "" {
		return ListStoriesResult{}, errors.New("epic ID is required")
	}

	limit := q.Limit
	if limit <= 0 {
		limit = 50
	}

	offset := max(q.Offset, 0)

	stories, total, err := h.planning.ListStories(ctx, q.EpicID, q.StateFilter, limit, offset)
	if err != nil {
		return ListStoriesResult{}, err
	}

	return ListStoriesResult{
		Stories:    stories,
		TotalCount: total,
	}, nil
}
