package command

import (
	"context"
	"errors"
	"fmt"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
)

// RejectDecisionCmd carries the inputs for rejecting a decision.
type RejectDecisionCmd struct {
	StoryID    string
	DecisionID string
	Reason     string
}

// RejectDecisionHandler orchestrates decision rejection via the fleet client.
type RejectDecisionHandler struct {
	client ports.FleetClient
}

// NewRejectDecisionHandler returns a handler wired to the given FleetClient.
func NewRejectDecisionHandler(client ports.FleetClient) *RejectDecisionHandler {
	return &RejectDecisionHandler{client: client}
}

// Handle validates the command and delegates to the fleet client.
func (h *RejectDecisionHandler) Handle(ctx context.Context, cmd RejectDecisionCmd) error {
	if cmd.StoryID == "" {
		return errors.New("reject_decision: story_id is required")
	}
	if cmd.DecisionID == "" {
		return errors.New("reject_decision: decision_id is required")
	}
	if cmd.Reason == "" {
		return errors.New("reject_decision: reason is required")
	}

	if err := h.client.RejectDecision(ctx, cmd.StoryID, cmd.DecisionID, cmd.Reason); err != nil {
		return fmt.Errorf("reject_decision: %w", err)
	}

	return nil
}
