package query

import (
	"context"
	"fmt"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// ListCeremoniesHandler returns ceremony instances with optional filtering.
type ListCeremoniesHandler struct {
	client ports.FleetClient
}

// NewListCeremoniesHandler returns a handler wired to the given FleetClient.
func NewListCeremoniesHandler(client ports.FleetClient) *ListCeremoniesHandler {
	return &ListCeremoniesHandler{client: client}
}

// Handle delegates to the fleet client and returns the matching ceremonies and total count.
func (h *ListCeremoniesHandler) Handle(ctx context.Context, storyID, statusFilter string, limit, offset int32) ([]domain.CeremonyStatus, int32, error) {
	ceremonies, total, err := h.client.ListCeremonies(ctx, storyID, statusFilter, limit, offset)
	if err != nil {
		return nil, 0, fmt.Errorf("list_ceremonies: %w", err)
	}
	return ceremonies, total, nil
}
