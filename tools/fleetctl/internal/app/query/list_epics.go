package query

import (
	"context"
	"fmt"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// ListEpicsHandler returns epics for a given project with optional filtering.
type ListEpicsHandler struct {
	client ports.FleetClient
}

// NewListEpicsHandler returns a handler wired to the given FleetClient.
func NewListEpicsHandler(client ports.FleetClient) *ListEpicsHandler {
	return &ListEpicsHandler{client: client}
}

// Handle delegates to the fleet client and returns the matching epics and total count.
func (h *ListEpicsHandler) Handle(ctx context.Context, projectID, statusFilter string, limit, offset int32) ([]domain.EpicSummary, int32, error) {
	epics, total, err := h.client.ListEpics(ctx, projectID, statusFilter, limit, offset)
	if err != nil {
		return nil, 0, fmt.Errorf("list_epics: %w", err)
	}
	return epics, total, nil
}
