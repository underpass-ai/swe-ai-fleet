package query

import (
	"context"
	"errors"
	"fmt"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// ListStoriesQuery carries the filter parameters for listing stories.
type ListStoriesQuery struct {
	EpicID string
}

// ListStoriesHandler retrieves stories belonging to a given epic from the
// fleet control plane.
type ListStoriesHandler struct {
	client ports.FleetClient
}

// NewListStoriesHandler returns a handler wired to the given FleetClient.
func NewListStoriesHandler(client ports.FleetClient) *ListStoriesHandler {
	return &ListStoriesHandler{client: client}
}

// Handle fetches stories for the specified epic.
func (h *ListStoriesHandler) Handle(ctx context.Context, q ListStoriesQuery) ([]domain.StorySummary, error) {
	if q.EpicID == "" {
		return nil, errors.New("list_stories: epic_id is required")
	}

	stories, _, err := h.client.ListStories(ctx, q.EpicID, "", 0, 0)
	if err != nil {
		return nil, fmt.Errorf("list_stories: %w", err)
	}
	return stories, nil
}
