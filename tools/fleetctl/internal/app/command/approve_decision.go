package command

import (
	"context"
	"errors"
	"fmt"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
)

// ApproveDecisionCmd carries the inputs for approving a decision.
type ApproveDecisionCmd struct {
	StoryID    string
	DecisionID string
	Comment    string
}

// ApproveDecisionHandler orchestrates decision approval via the fleet client.
type ApproveDecisionHandler struct {
	client ports.FleetClient
}

// NewApproveDecisionHandler returns a handler wired to the given FleetClient.
func NewApproveDecisionHandler(client ports.FleetClient) *ApproveDecisionHandler {
	return &ApproveDecisionHandler{client: client}
}

// Handle validates the command and delegates to the fleet client.
func (h *ApproveDecisionHandler) Handle(ctx context.Context, cmd ApproveDecisionCmd) error {
	if cmd.StoryID == "" {
		return errors.New("approve_decision: story_id is required")
	}
	if cmd.DecisionID == "" {
		return errors.New("approve_decision: decision_id is required")
	}

	if err := h.client.ApproveDecision(ctx, cmd.StoryID, cmd.DecisionID, cmd.Comment); err != nil {
		return fmt.Errorf("approve_decision: %w", err)
	}

	return nil
}
