package query

import (
	"context"
	"errors"
	"fmt"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// ListTasksQuery carries the filter parameters for listing tasks.
type ListTasksQuery struct {
	StoryID string
}

// ListTasksHandler retrieves tasks belonging to a given story from the
// fleet control plane.
type ListTasksHandler struct {
	client ports.FleetClient
}

// NewListTasksHandler returns a handler wired to the given FleetClient.
func NewListTasksHandler(client ports.FleetClient) *ListTasksHandler {
	return &ListTasksHandler{client: client}
}

// Handle fetches tasks for the specified story.
func (h *ListTasksHandler) Handle(ctx context.Context, q ListTasksQuery) ([]domain.TaskSummary, error) {
	if q.StoryID == "" {
		return nil, errors.New("list_tasks: story_id is required")
	}

	tasks, _, err := h.client.ListTasks(ctx, q.StoryID, "", 0, 0)
	if err != nil {
		return nil, fmt.Errorf("list_tasks: %w", err)
	}
	return tasks, nil
}
