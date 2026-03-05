package query

import (
	"context"
	"fmt"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// ListStoriesHandler retrieves stories belonging to a given epic from the
// fleet control plane.
type ListStoriesHandler struct {
	client ports.FleetClient
}

// NewListStoriesHandler returns a handler wired to the given FleetClient.
func NewListStoriesHandler(client ports.FleetClient) *ListStoriesHandler {
	return &ListStoriesHandler{client: client}
}

// Handle fetches stories for the specified epic with optional filtering and pagination.
func (h *ListStoriesHandler) Handle(ctx context.Context, epicID, stateFilter string, limit, offset int32) ([]domain.StorySummary, int32, error) {
	stories, total, err := h.client.ListStories(ctx, epicID, stateFilter, limit, offset)
	if err != nil {
		return nil, 0, fmt.Errorf("list_stories: %w", err)
	}
	return stories, total, nil
}
