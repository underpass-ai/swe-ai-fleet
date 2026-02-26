package command

import (
	"context"
	"errors"
	"fmt"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// StartCeremonyCmd carries the inputs for starting a ceremony instance.
type StartCeremonyCmd struct {
	CeremonyID     string
	DefinitionName string
	StoryID        string
	StepIDs        []string
}

// StartCeremonyHandler orchestrates ceremony startup via the fleet client.
type StartCeremonyHandler struct {
	client ports.FleetClient
}

// NewStartCeremonyHandler returns a handler wired to the given FleetClient.
func NewStartCeremonyHandler(client ports.FleetClient) *StartCeremonyHandler {
	return &StartCeremonyHandler{client: client}
}

// Handle validates the command, generates a request ID, and delegates to
// the fleet client. It returns the initial ceremony status.
func (h *StartCeremonyHandler) Handle(ctx context.Context, cmd StartCeremonyCmd) (domain.CeremonyStatus, error) {
	if cmd.CeremonyID == "" {
		return domain.CeremonyStatus{}, errors.New("start_ceremony: ceremony_id is required")
	}
	if cmd.DefinitionName == "" {
		return domain.CeremonyStatus{}, errors.New("start_ceremony: definition_name is required")
	}
	if cmd.StoryID == "" {
		return domain.CeremonyStatus{}, errors.New("start_ceremony: story_id is required")
	}
	if len(cmd.StepIDs) == 0 {
		return domain.CeremonyStatus{}, errors.New("start_ceremony: at least one step_id is required")
	}

	requestID, err := generateRequestID()
	if err != nil {
		return domain.CeremonyStatus{}, fmt.Errorf("start_ceremony: failed to generate request id: %w", err)
	}

	status, err := h.client.StartCeremony(ctx, requestID, cmd.CeremonyID, cmd.DefinitionName, cmd.StoryID, cmd.StepIDs)
	if err != nil {
		return domain.CeremonyStatus{}, fmt.Errorf("start_ceremony: %w", err)
	}

	return status, nil
}
