package command

import (
	"context"
	"errors"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

// CreateEpicCmd carries the parameters for creating a new epic.
type CreateEpicCmd struct {
	RequestID   string
	ProjectID   string
	Title       string
	Description string
	RequestedBy string
}

// Validate checks that all required fields are present.
func (c CreateEpicCmd) Validate() error {
	if c.RequestID == "" {
		return errors.New("request ID is required")
	}
	if c.ProjectID == "" {
		return errors.New("project ID is required")
	}
	if c.Title == "" {
		return errors.New("epic title is required")
	}
	if c.RequestedBy == "" {
		return errors.New("requestedBy is required")
	}
	return nil
}

// CreateEpicHandler orchestrates epic creation.
type CreateEpicHandler struct {
	planning ports.PlanningClient
	audit    ports.AuditLogger
}

// NewCreateEpicHandler wires the handler to its ports.
func NewCreateEpicHandler(p ports.PlanningClient, a ports.AuditLogger) *CreateEpicHandler {
	return &CreateEpicHandler{planning: p, audit: a}
}

// Handle validates the command, delegates to the planning port, and records
// an audit event. It returns the newly created epic ID.
func (h *CreateEpicHandler) Handle(ctx context.Context, cmd CreateEpicCmd) (string, error) {
	if err := cmd.Validate(); err != nil {
		h.recordAudit(ctx, cmd.RequestID, cmd.RequestedBy, false, err.Error())
		return "", err
	}

	epicID, err := h.planning.CreateEpic(ctx, cmd.ProjectID, cmd.Title, cmd.Description)
	if err != nil {
		h.recordAudit(ctx, cmd.RequestID, cmd.RequestedBy, false, err.Error())
		return "", err
	}

	h.recordAudit(ctx, cmd.RequestID, cmd.RequestedBy, true, "")
	return epicID, nil
}

func (h *CreateEpicHandler) recordAudit(ctx context.Context, requestID, clientID string, success bool, errMsg string) {
	h.audit.Record(ctx, ports.AuditEvent{
		ClientID:  clientID,
		Method:    "CreateEpic",
		RequestID: requestID,
		Timestamp: time.Now(),
		Success:   success,
		Error:     errMsg,
	})
}
