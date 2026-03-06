package command

import (
	"context"
	"errors"
	"fmt"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// CreateTaskCmd carries the inputs for creating a new task.
type CreateTaskCmd struct {
	StoryID        string
	Title          string
	Description    string
	TaskType       string
	AssignedTo     string
	EstimatedHours int32
	Priority       int32
}

// CreateTaskHandler orchestrates task creation via the fleet client.
type CreateTaskHandler struct {
	client ports.FleetClient
}

// NewCreateTaskHandler returns a handler wired to the given FleetClient.
func NewCreateTaskHandler(client ports.FleetClient) *CreateTaskHandler {
	return &CreateTaskHandler{client: client}
}

// Handle validates the command, generates a request ID, and delegates to
// the fleet client. It returns the created task summary.
func (h *CreateTaskHandler) Handle(ctx context.Context, cmd CreateTaskCmd) (domain.TaskSummary, error) {
	if cmd.StoryID == "" {
		return domain.TaskSummary{}, errors.New("create_task: story_id is required")
	}
	if cmd.Title == "" {
		return domain.TaskSummary{}, errors.New("create_task: title is required")
	}

	requestID, err := generateRequestID()
	if err != nil {
		return domain.TaskSummary{}, fmt.Errorf("create_task: failed to generate request id: %w", err)
	}

	task, err := h.client.CreateTask(ctx, ports.CreateTaskInput{
		RequestID:      requestID,
		StoryID:        cmd.StoryID,
		Title:          cmd.Title,
		Description:    cmd.Description,
		TaskType:       cmd.TaskType,
		AssignedTo:     cmd.AssignedTo,
		EstimatedHours: cmd.EstimatedHours,
		Priority:       cmd.Priority,
	})
	if err != nil {
		return domain.TaskSummary{}, fmt.Errorf("create_task: %w", err)
	}

	return task, nil
}
