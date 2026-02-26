package command

import (
	"context"
	"errors"
	"fmt"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
)

// TransitionStoryCmd carries the inputs for transitioning a story to a
// new state.
type TransitionStoryCmd struct {
	StoryID     string
	TargetState string
}

// TransitionStoryHandler orchestrates story state transitions.
type TransitionStoryHandler struct {
	client ports.FleetClient
}

// NewTransitionStoryHandler returns a handler wired to the given FleetClient.
func NewTransitionStoryHandler(client ports.FleetClient) *TransitionStoryHandler {
	return &TransitionStoryHandler{client: client}
}

// Handle validates the command and delegates to the fleet client.
func (h *TransitionStoryHandler) Handle(ctx context.Context, cmd TransitionStoryCmd) error {
	if cmd.StoryID == "" {
		return errors.New("transition_story: story_id is required")
	}
	if cmd.TargetState == "" {
		return errors.New("transition_story: target_state is required")
	}

	if err := h.client.TransitionStory(ctx, cmd.StoryID, cmd.TargetState); err != nil {
		return fmt.Errorf("transition_story: %w", err)
	}

	return nil
}
