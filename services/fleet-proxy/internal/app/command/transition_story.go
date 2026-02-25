package command

import (
	"context"
	"errors"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

// TransitionStoryCmd carries the parameters for transitioning a story to a new state.
type TransitionStoryCmd struct {
	StoryID     string
	TargetState string
	RequestedBy string
}

// Validate checks that all required fields are present.
func (c TransitionStoryCmd) Validate() error {
	if c.StoryID == "" {
		return errors.New("story ID is required")
	}
	if c.TargetState == "" {
		return errors.New("target state is required")
	}
	if c.RequestedBy == "" {
		return errors.New("requestedBy is required")
	}
	return nil
}

// TransitionStoryHandler orchestrates story state transitions.
type TransitionStoryHandler struct {
	planning ports.PlanningClient
	audit    ports.AuditLogger
}

// NewTransitionStoryHandler wires the handler to its ports.
func NewTransitionStoryHandler(p ports.PlanningClient, a ports.AuditLogger) *TransitionStoryHandler {
	return &TransitionStoryHandler{planning: p, audit: a}
}

// Handle validates the command, delegates to the planning port, and records
// an audit event.
func (h *TransitionStoryHandler) Handle(ctx context.Context, cmd TransitionStoryCmd) error {
	if err := cmd.Validate(); err != nil {
		h.recordAudit(ctx, cmd.StoryID, cmd.RequestedBy, false, err.Error())
		return err
	}

	if err := h.planning.TransitionStory(ctx, cmd.StoryID, cmd.TargetState); err != nil {
		h.recordAudit(ctx, cmd.StoryID, cmd.RequestedBy, false, err.Error())
		return err
	}

	h.recordAudit(ctx, cmd.StoryID, cmd.RequestedBy, true, "")
	return nil
}

func (h *TransitionStoryHandler) recordAudit(ctx context.Context, requestID, clientID string, success bool, errMsg string) {
	h.audit.Record(ctx, ports.AuditEvent{
		ClientID:  clientID,
		Method:    "TransitionStory",
		RequestID: requestID,
		Timestamp: time.Now(),
		Success:   success,
		Error:     errMsg,
	})
}
