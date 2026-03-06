package query

import (
	"context"
	"errors"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

// ListEpicsQuery carries the parameters for listing epics.
type ListEpicsQuery struct {
	ProjectID    string
	StatusFilter string
	Limit        int32
	Offset       int32
}

// ListEpicsResult wraps a page of epics with total count for pagination.
type ListEpicsResult struct {
	Epics      []ports.EpicResult
	TotalCount int32
}

// ListEpicsHandler handles epic listing queries.
type ListEpicsHandler struct {
	planning ports.PlanningClient
}

// NewListEpicsHandler wires the handler to the planning port.
func NewListEpicsHandler(p ports.PlanningClient) *ListEpicsHandler {
	return &ListEpicsHandler{planning: p}
}

// Handle validates the query and delegates to the planning port.
func (h *ListEpicsHandler) Handle(ctx context.Context, q ListEpicsQuery) (ListEpicsResult, error) {
	if q.ProjectID == "" {
		return ListEpicsResult{}, errors.New("project ID is required")
	}

	limit := q.Limit
	if limit <= 0 {
		limit = 50
	}

	offset := max(q.Offset, 0)

	epics, total, err := h.planning.ListEpics(ctx, q.ProjectID, q.StatusFilter, limit, offset)
	if err != nil {
		return ListEpicsResult{}, err
	}

	return ListEpicsResult{
		Epics:      epics,
		TotalCount: total,
	}, nil
}
