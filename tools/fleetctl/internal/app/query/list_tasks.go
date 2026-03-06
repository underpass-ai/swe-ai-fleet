package query

import (
	"context"
	"fmt"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// ListTasksHandler retrieves tasks belonging to a given story from the
// fleet control plane.
type ListTasksHandler struct {
	client ports.FleetClient
}

// NewListTasksHandler returns a handler wired to the given FleetClient.
func NewListTasksHandler(client ports.FleetClient) *ListTasksHandler {
	return &ListTasksHandler{client: client}
}

// Handle fetches tasks for the specified story with optional filtering and pagination.
func (h *ListTasksHandler) Handle(ctx context.Context, storyID, statusFilter string, limit, offset int32) ([]domain.TaskSummary, int32, error) {
	tasks, total, err := h.client.ListTasks(ctx, storyID, statusFilter, limit, offset)
	if err != nil {
		return nil, 0, fmt.Errorf("list_tasks: %w", err)
	}
	return tasks, total, nil
}
