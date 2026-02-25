// Package command contains the write-side (command) handlers for the
// fleet-proxy application layer. Each handler validates its input, delegates
// to one or more ports, and records an audit event.
package command

import (
	"context"
	"errors"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

// CreateProjectCmd carries the parameters for creating a new project.
type CreateProjectCmd struct {
	RequestID   string
	Name        string
	Description string
	RequestedBy string
}

// Validate checks that all required fields are present.
func (c CreateProjectCmd) Validate() error {
	if c.RequestID == "" {
		return errors.New("request ID is required")
	}
	if c.Name == "" {
		return errors.New("project name is required")
	}
	if c.RequestedBy == "" {
		return errors.New("requestedBy is required")
	}
	return nil
}

// CreateProjectHandler orchestrates project creation.
type CreateProjectHandler struct {
	planning ports.PlanningClient
	audit    ports.AuditLogger
}

// NewCreateProjectHandler wires the handler to its ports.
func NewCreateProjectHandler(p ports.PlanningClient, a ports.AuditLogger) *CreateProjectHandler {
	return &CreateProjectHandler{planning: p, audit: a}
}

// Handle validates the command, delegates to the planning port, and records
// an audit event. It returns the newly created project ID.
func (h *CreateProjectHandler) Handle(ctx context.Context, cmd CreateProjectCmd) (string, error) {
	if err := cmd.Validate(); err != nil {
		h.recordAudit(ctx, cmd.RequestID, cmd.RequestedBy, false, err.Error())
		return "", err
	}

	projectID, err := h.planning.CreateProject(ctx, cmd.Name, cmd.Description)
	if err != nil {
		h.recordAudit(ctx, cmd.RequestID, cmd.RequestedBy, false, err.Error())
		return "", err
	}

	h.recordAudit(ctx, cmd.RequestID, cmd.RequestedBy, true, "")
	return projectID, nil
}

func (h *CreateProjectHandler) recordAudit(ctx context.Context, requestID, clientID string, success bool, errMsg string) {
	h.audit.Record(ctx, ports.AuditEvent{
		ClientID:  clientID,
		Method:    "CreateProject",
		RequestID: requestID,
		Timestamp: time.Now(),
		Success:   success,
		Error:     errMsg,
	})
}
