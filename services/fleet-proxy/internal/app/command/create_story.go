package command

import (
	"context"
	"errors"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

// CreateStoryCmd carries the parameters for creating a new story.
type CreateStoryCmd struct {
	RequestID   string
	EpicID      string
	Title       string
	Brief       string
	RequestedBy string
}

// Validate checks that all required fields are present.
func (c CreateStoryCmd) Validate() error {
	if c.RequestID == "" {
		return errors.New("request ID is required")
	}
	if c.EpicID == "" {
		return errors.New("epic ID is required")
	}
	if c.Title == "" {
		return errors.New("story title is required")
	}
	if c.RequestedBy == "" {
		return errors.New("requestedBy is required")
	}
	return nil
}

// CreateStoryHandler orchestrates story creation.
type CreateStoryHandler struct {
	planning ports.PlanningClient
	audit    ports.AuditLogger
}

// NewCreateStoryHandler wires the handler to its ports.
func NewCreateStoryHandler(p ports.PlanningClient, a ports.AuditLogger) *CreateStoryHandler {
	return &CreateStoryHandler{planning: p, audit: a}
}

// Handle validates the command, delegates to the planning port, and records
// an audit event. It returns the newly created story ID.
func (h *CreateStoryHandler) Handle(ctx context.Context, cmd CreateStoryCmd) (string, error) {
	if err := cmd.Validate(); err != nil {
		h.recordAudit(ctx, cmd.RequestID, cmd.RequestedBy, false, err.Error())
		return "", err
	}

	storyID, err := h.planning.CreateStory(ctx, cmd.EpicID, cmd.Title, cmd.Brief)
	if err != nil {
		h.recordAudit(ctx, cmd.RequestID, cmd.RequestedBy, false, err.Error())
		return "", err
	}

	h.recordAudit(ctx, cmd.RequestID, cmd.RequestedBy, true, "")
	return storyID, nil
}

func (h *CreateStoryHandler) recordAudit(ctx context.Context, requestID, clientID string, success bool, errMsg string) {
	h.audit.Record(ctx, ports.AuditEvent{
		ClientID:  clientID,
		Method:    "CreateStory",
		RequestID: requestID,
		Timestamp: time.Now(),
		Success:   success,
		Error:     errMsg,
	})
}
