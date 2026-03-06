package query

import (
	"context"
	"fmt"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// ListProjectsHandler retrieves all projects visible to the authenticated
// identity from the fleet control plane.
type ListProjectsHandler struct {
	client ports.FleetClient
}

// NewListProjectsHandler returns a handler wired to the given FleetClient.
func NewListProjectsHandler(client ports.FleetClient) *ListProjectsHandler {
	return &ListProjectsHandler{client: client}
}

// Handle fetches a page of projects. Visibility is determined server-side
// from the mTLS identity.
func (h *ListProjectsHandler) Handle(ctx context.Context, statusFilter string, limit, offset int32) ([]domain.ProjectSummary, int32, error) {
	projects, total, err := h.client.ListProjects(ctx, statusFilter, limit, offset)
	if err != nil {
		return nil, 0, fmt.Errorf("list_projects: %w", err)
	}
	return projects, total, nil
}
