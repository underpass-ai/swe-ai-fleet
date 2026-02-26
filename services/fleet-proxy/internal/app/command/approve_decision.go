package command

import (
	"context"
	"errors"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

// ApproveDecisionCmd carries the parameters for approving a pending decision.
type ApproveDecisionCmd struct {
	StoryID     string
	DecisionID  string
	Comment     string
	RequestedBy string
}

// Validate checks that all required fields are present.
func (c ApproveDecisionCmd) Validate() error {
	if c.StoryID == "" {
		return errors.New("story ID is required")
	}
	if c.DecisionID == "" {
		return errors.New("decision ID is required")
	}
	if c.RequestedBy == "" {
		return errors.New("requestedBy is required")
	}
	return nil
}

// ApproveDecisionHandler orchestrates decision approval.
type ApproveDecisionHandler struct {
	planning ports.PlanningClient
	audit    ports.AuditLogger
}

// NewApproveDecisionHandler wires the handler to its ports.
func NewApproveDecisionHandler(p ports.PlanningClient, a ports.AuditLogger) *ApproveDecisionHandler {
	return &ApproveDecisionHandler{planning: p, audit: a}
}

// Handle validates the command, delegates to the planning port, and records
// an audit event.
func (h *ApproveDecisionHandler) Handle(ctx context.Context, cmd ApproveDecisionCmd) error {
	if err := cmd.Validate(); err != nil {
		h.recordAudit(ctx, cmd.DecisionID, cmd.RequestedBy, false, err.Error())
		return err
	}

	if err := h.planning.ApproveDecision(ctx, cmd.StoryID, cmd.DecisionID, cmd.Comment); err != nil {
		h.recordAudit(ctx, cmd.DecisionID, cmd.RequestedBy, false, err.Error())
		return err
	}

	h.recordAudit(ctx, cmd.DecisionID, cmd.RequestedBy, true, "")
	return nil
}

func (h *ApproveDecisionHandler) recordAudit(ctx context.Context, requestID, clientID string, success bool, errMsg string) {
	h.audit.Record(ctx, ports.AuditEvent{
		ClientID:  clientID,
		Method:    "ApproveDecision",
		RequestID: requestID,
		Timestamp: time.Now(),
		Success:   success,
		Error:     errMsg,
	})
}
