package command

import (
	"context"
	"errors"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

// CreateTaskCmd carries the parameters for creating a new task.
type CreateTaskCmd struct {
	RequestID      string
	StoryID        string
	Title          string
	Description    string
	Type           string
	AssignedTo     string
	EstimatedHours int32
	Priority       int32
	RequestedBy    string
}

// Validate checks that all required fields are present.
func (c CreateTaskCmd) Validate() error {
	if c.RequestID == "" {
		return errors.New("request ID is required")
	}
	if c.StoryID == "" {
		return errors.New("story ID is required")
	}
	if c.Title == "" {
		return errors.New("task title is required")
	}
	if c.Type == "" {
		return errors.New("task type is required")
	}
	if c.RequestedBy == "" {
		return errors.New("requestedBy is required")
	}
	if c.Priority < 0 {
		return errors.New("priority must be non-negative")
	}
	if c.EstimatedHours < 0 {
		return errors.New("estimated hours must be non-negative")
	}
	return nil
}

// CreateTaskHandler orchestrates task creation.
type CreateTaskHandler struct {
	planning ports.PlanningClient
	audit    ports.AuditLogger
}

// NewCreateTaskHandler wires the handler to its ports.
func NewCreateTaskHandler(p ports.PlanningClient, a ports.AuditLogger) *CreateTaskHandler {
	return &CreateTaskHandler{planning: p, audit: a}
}

// Handle validates the command, delegates to the planning port, and records
// an audit event. It returns the newly created task ID.
func (h *CreateTaskHandler) Handle(ctx context.Context, cmd CreateTaskCmd) (string, error) {
	if err := cmd.Validate(); err != nil {
		h.recordAudit(ctx, cmd.RequestID, cmd.RequestedBy, false, err.Error())
		return "", err
	}

	taskID, err := h.planning.CreateTask(
		ctx,
		cmd.StoryID,
		cmd.Title,
		cmd.Description,
		cmd.Type,
		cmd.AssignedTo,
		cmd.EstimatedHours,
		cmd.Priority,
	)
	if err != nil {
		h.recordAudit(ctx, cmd.RequestID, cmd.RequestedBy, false, err.Error())
		return "", err
	}

	h.recordAudit(ctx, cmd.RequestID, cmd.RequestedBy, true, "")
	return taskID, nil
}

func (h *CreateTaskHandler) recordAudit(ctx context.Context, requestID, clientID string, success bool, errMsg string) {
	h.audit.Record(ctx, ports.AuditEvent{
		ClientID:  clientID,
		Method:    "CreateTask",
		RequestID: requestID,
		Timestamp: time.Now(),
		Success:   success,
		Error:     errMsg,
	})
}
