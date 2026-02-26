package command

import (
	"context"
	"errors"
	"fmt"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// CreateStoryCmd carries the inputs for creating a new story.
type CreateStoryCmd struct {
	EpicID string
	Title  string
	Brief  string
}

// CreateStoryHandler orchestrates story creation via the fleet client.
type CreateStoryHandler struct {
	client ports.FleetClient
}

// NewCreateStoryHandler returns a handler wired to the given FleetClient.
func NewCreateStoryHandler(client ports.FleetClient) *CreateStoryHandler {
	return &CreateStoryHandler{client: client}
}

// Handle validates the command, generates a request ID, and delegates to
// the fleet client. It returns the created story summary.
func (h *CreateStoryHandler) Handle(ctx context.Context, cmd CreateStoryCmd) (domain.StorySummary, error) {
	if cmd.EpicID == "" {
		return domain.StorySummary{}, errors.New("create_story: epic_id is required")
	}
	if cmd.Title == "" {
		return domain.StorySummary{}, errors.New("create_story: title is required")
	}

	requestID, err := generateRequestID()
	if err != nil {
		return domain.StorySummary{}, fmt.Errorf("create_story: failed to generate request id: %w", err)
	}

	story, err := h.client.CreateStory(ctx, requestID, cmd.EpicID, cmd.Title, cmd.Brief)
	if err != nil {
		return domain.StorySummary{}, fmt.Errorf("create_story: %w", err)
	}

	return story, nil
}
