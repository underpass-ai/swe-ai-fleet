// Package query contains the read-side (query) handlers for the fleet-proxy
// application layer. Each handler validates its input and delegates to the
// appropriate port to fetch data.
package query

import (
	"context"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

// ListProjectsQuery carries the parameters for listing projects.
type ListProjectsQuery struct {
	StatusFilter string
	Limit        int32
	Offset       int32
}

// ListProjectsResult wraps a page of projects with total count for pagination.
type ListProjectsResult struct {
	Projects   []ports.ProjectResult
	TotalCount int32
}

// ListProjectsHandler handles project listing queries.
type ListProjectsHandler struct {
	planning ports.PlanningClient
}

// NewListProjectsHandler wires the handler to the planning port.
func NewListProjectsHandler(p ports.PlanningClient) *ListProjectsHandler {
	return &ListProjectsHandler{planning: p}
}

// Handle executes the query, applying default pagination if limits are not set.
func (h *ListProjectsHandler) Handle(ctx context.Context, q ListProjectsQuery) (ListProjectsResult, error) {
	limit := q.Limit
	if limit <= 0 {
		limit = 50
	}
	offset := max(q.Offset, 0)

	projects, total, err := h.planning.ListProjects(ctx, q.StatusFilter, limit, offset)
	if err != nil {
		return ListProjectsResult{}, err
	}

	return ListProjectsResult{
		Projects:   projects,
		TotalCount: total,
	}, nil
}
