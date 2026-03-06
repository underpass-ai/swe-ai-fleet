package command

import (
	"context"
	"errors"
	"fmt"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// CreateEpicCmd carries the inputs for creating a new epic.
type CreateEpicCmd struct {
	ProjectID   string
	Title       string
	Description string
}

// CreateEpicHandler orchestrates epic creation via the fleet client.
type CreateEpicHandler struct {
	client ports.FleetClient
}

// NewCreateEpicHandler returns a handler wired to the given FleetClient.
func NewCreateEpicHandler(client ports.FleetClient) *CreateEpicHandler {
	return &CreateEpicHandler{client: client}
}

// Handle validates the command, generates a request ID, and delegates to
// the fleet client. It returns the created epic summary.
func (h *CreateEpicHandler) Handle(ctx context.Context, cmd CreateEpicCmd) (domain.EpicSummary, error) {
	if cmd.ProjectID == "" {
		return domain.EpicSummary{}, errors.New("create_epic: project_id is required")
	}
	if cmd.Title == "" {
		return domain.EpicSummary{}, errors.New("create_epic: title is required")
	}

	requestID, err := generateRequestID()
	if err != nil {
		return domain.EpicSummary{}, fmt.Errorf("create_epic: failed to generate request id: %w", err)
	}

	epic, err := h.client.CreateEpic(ctx, requestID, cmd.ProjectID, cmd.Title, cmd.Description)
	if err != nil {
		return domain.EpicSummary{}, fmt.Errorf("create_epic: %w", err)
	}

	return epic, nil
}
