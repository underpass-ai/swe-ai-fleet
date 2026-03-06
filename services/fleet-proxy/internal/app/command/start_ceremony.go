package command

import (
	"context"
	"errors"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

// StartCeremonyCmd carries the parameters for starting a ceremony instance.
type StartCeremonyCmd struct {
	RequestID      string
	CeremonyID     string
	DefinitionName string
	StoryID        string
	StepIDs        []string
	RequestedBy    string
}

// Validate checks that all required fields are present.
func (c StartCeremonyCmd) Validate() error {
	if c.RequestID == "" {
		return errors.New("request ID is required")
	}
	if c.CeremonyID == "" {
		return errors.New("ceremony ID is required")
	}
	if c.DefinitionName == "" {
		return errors.New("definition name is required")
	}
	if c.StoryID == "" {
		return errors.New("story ID is required")
	}
	if len(c.StepIDs) == 0 {
		return errors.New("at least one step ID is required")
	}
	if c.RequestedBy == "" {
		return errors.New("requestedBy is required")
	}
	return nil
}

// StartCeremonyHandler orchestrates starting a ceremony.
type StartCeremonyHandler struct {
	ceremony ports.CeremonyClient
	audit    ports.AuditLogger
}

// NewStartCeremonyHandler wires the handler to its ports.
func NewStartCeremonyHandler(c ports.CeremonyClient, a ports.AuditLogger) *StartCeremonyHandler {
	return &StartCeremonyHandler{ceremony: c, audit: a}
}

// Handle validates the command, delegates to the ceremony port, and records
// an audit event. It returns the ceremony instance ID.
func (h *StartCeremonyHandler) Handle(ctx context.Context, cmd StartCeremonyCmd) (string, error) {
	if err := cmd.Validate(); err != nil {
		h.recordAudit(ctx, cmd.RequestID, cmd.RequestedBy, false, err.Error())
		return "", err
	}

	instanceID, err := h.ceremony.StartCeremony(ctx, cmd.CeremonyID, cmd.DefinitionName, cmd.StoryID, cmd.StepIDs)
	if err != nil {
		h.recordAudit(ctx, cmd.RequestID, cmd.RequestedBy, false, err.Error())
		return "", err
	}

	h.recordAudit(ctx, cmd.RequestID, cmd.RequestedBy, true, "")
	return instanceID, nil
}

func (h *StartCeremonyHandler) recordAudit(ctx context.Context, requestID, clientID string, success bool, errMsg string) {
	h.audit.Record(ctx, ports.AuditEvent{
		ClientID:  clientID,
		Method:    "StartCeremony",
		RequestID: requestID,
		Timestamp: time.Now(),
		Success:   success,
		Error:     errMsg,
	})
}
