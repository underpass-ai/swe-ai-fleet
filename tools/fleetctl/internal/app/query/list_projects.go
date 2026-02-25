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

// Handle fetches the project list. It takes no query parameters because
// visibility is determined server-side from the mTLS identity.
func (h *ListProjectsHandler) Handle(ctx context.Context) ([]domain.ProjectSummary, error) {
	projects, err := h.client.ListProjects(ctx)
	if err != nil {
		return nil, fmt.Errorf("list_projects: %w", err)
	}
	return projects, nil
}
