package query

import (
	"context"
	"errors"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

// ListTasksQuery carries the parameters for listing tasks.
type ListTasksQuery struct {
	StoryID      string
	StatusFilter string
	Limit        int32
	Offset       int32
}

// ListTasksResult wraps a page of tasks with total count for pagination.
type ListTasksResult struct {
	Tasks      []ports.TaskResult
	TotalCount int32
}

// ListTasksHandler handles task listing queries.
type ListTasksHandler struct {
	planning ports.PlanningClient
}

// NewListTasksHandler wires the handler to the planning port.
func NewListTasksHandler(p ports.PlanningClient) *ListTasksHandler {
	return &ListTasksHandler{planning: p}
}

// Handle validates the query and delegates to the planning port.
func (h *ListTasksHandler) Handle(ctx context.Context, q ListTasksQuery) (ListTasksResult, error) {
	if q.StoryID == "" {
		return ListTasksResult{}, errors.New("story ID is required")
	}

	limit := q.Limit
	if limit <= 0 {
		limit = 50
	}

	offset := max(q.Offset, 0)

	tasks, total, err := h.planning.ListTasks(ctx, q.StoryID, q.StatusFilter, limit, offset)
	if err != nil {
		return ListTasksResult{}, err
	}

	return ListTasksResult{
		Tasks:      tasks,
		TotalCount: total,
	}, nil
}
