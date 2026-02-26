package command

import (
	"context"
	"errors"
	"fmt"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// CreateProjectCmd carries the inputs for creating a new project.
type CreateProjectCmd struct {
	Name        string
	Description string
}

// CreateProjectHandler orchestrates project creation via the fleet client.
type CreateProjectHandler struct {
	client ports.FleetClient
}

// NewCreateProjectHandler returns a handler wired to the given FleetClient.
func NewCreateProjectHandler(client ports.FleetClient) *CreateProjectHandler {
	return &CreateProjectHandler{client: client}
}

// Handle validates the command, generates a request ID, and delegates to
// the fleet client. It returns the created project summary.
func (h *CreateProjectHandler) Handle(ctx context.Context, cmd CreateProjectCmd) (domain.ProjectSummary, error) {
	if cmd.Name == "" {
		return domain.ProjectSummary{}, errors.New("create_project: name is required")
	}

	requestID, err := generateRequestID()
	if err != nil {
		return domain.ProjectSummary{}, fmt.Errorf("create_project: failed to generate request id: %w", err)
	}

	project, err := h.client.CreateProject(ctx, requestID, cmd.Name, cmd.Description)
	if err != nil {
		return domain.ProjectSummary{}, fmt.Errorf("create_project: %w", err)
	}

	return project, nil
}
