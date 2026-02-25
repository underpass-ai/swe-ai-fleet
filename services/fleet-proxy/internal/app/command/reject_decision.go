package command

import (
	"context"
	"errors"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

// RejectDecisionCmd carries the parameters for rejecting a pending decision.
type RejectDecisionCmd struct {
	StoryID     string
	DecisionID  string
	Reason      string
	RequestedBy string
}

// Validate checks that all required fields are present.
func (c RejectDecisionCmd) Validate() error {
	if c.StoryID == "" {
		return errors.New("story ID is required")
	}
	if c.DecisionID == "" {
		return errors.New("decision ID is required")
	}
	if c.Reason == "" {
		return errors.New("rejection reason is required")
	}
	if c.RequestedBy == "" {
		return errors.New("requestedBy is required")
	}
	return nil
}

// RejectDecisionHandler orchestrates decision rejection.
type RejectDecisionHandler struct {
	planning ports.PlanningClient
	audit    ports.AuditLogger
}

// NewRejectDecisionHandler wires the handler to its ports.
func NewRejectDecisionHandler(p ports.PlanningClient, a ports.AuditLogger) *RejectDecisionHandler {
	return &RejectDecisionHandler{planning: p, audit: a}
}

// Handle validates the command, delegates to the planning port, and records
// an audit event.
func (h *RejectDecisionHandler) Handle(ctx context.Context, cmd RejectDecisionCmd) error {
	if err := cmd.Validate(); err != nil {
		h.recordAudit(ctx, cmd.DecisionID, cmd.RequestedBy, false, err.Error())
		return err
	}

	if err := h.planning.RejectDecision(ctx, cmd.StoryID, cmd.DecisionID, cmd.Reason); err != nil {
		h.recordAudit(ctx, cmd.DecisionID, cmd.RequestedBy, false, err.Error())
		return err
	}

	h.recordAudit(ctx, cmd.DecisionID, cmd.RequestedBy, true, "")
	return nil
}

func (h *RejectDecisionHandler) recordAudit(ctx context.Context, requestID, clientID string, success bool, errMsg string) {
	h.audit.Record(ctx, ports.AuditEvent{
		ClientID:  clientID,
		Method:    "RejectDecision",
		RequestID: requestID,
		Timestamp: time.Now(),
		Success:   success,
		Error:     errMsg,
	})
}
