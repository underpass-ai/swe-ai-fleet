package command

import (
	"context"
	"errors"
	"strings"
	"testing"
)

func TestCreateTaskHandler_Handle(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name      string
		cmd       CreateTaskCmd
		planning  *flexPlanningClient
		wantErr   bool
		errSubstr string
		wantID    string
	}{
		{
			name: "successful creation",
			cmd: CreateTaskCmd{
				RequestID:      "req-1",
				StoryID:        "story-1",
				Title:          "Task Title",
				Description:    "Task description",
				Type:           "development",
				AssignedTo:     "agent-1",
				EstimatedHours: 4,
				Priority:       1,
				RequestedBy:    "user-1",
			},
			planning: &flexPlanningClient{createTaskID: "task-abc"},
			wantID:   "task-abc",
		},
		{
			name: "successful creation with zero optional fields",
			cmd: CreateTaskCmd{
				RequestID:   "req-2",
				StoryID:     "story-1",
				Title:       "Task",
				Type:        "review",
				RequestedBy: "user-1",
			},
			planning: &flexPlanningClient{createTaskID: "task-def"},
			wantID:   "task-def",
		},
		{
			name: "empty request ID",
			cmd: CreateTaskCmd{
				RequestID:   "",
				StoryID:     "story-1",
				Title:       "Task",
				Type:        "dev",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "request ID is required",
		},
		{
			name: "empty story ID",
			cmd: CreateTaskCmd{
				RequestID:   "req-1",
				StoryID:     "",
				Title:       "Task",
				Type:        "dev",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "story ID is required",
		},
		{
			name: "empty title",
			cmd: CreateTaskCmd{
				RequestID:   "req-1",
				StoryID:     "story-1",
				Title:       "",
				Type:        "dev",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "task title is required",
		},
		{
			name: "empty type",
			cmd: CreateTaskCmd{
				RequestID:   "req-1",
				StoryID:     "story-1",
				Title:       "Task",
				Type:        "",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "task type is required",
		},
		{
			name: "empty requestedBy",
			cmd: CreateTaskCmd{
				RequestID:   "req-1",
				StoryID:     "story-1",
				Title:       "Task",
				Type:        "dev",
				RequestedBy: "",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "requestedBy is required",
		},
		{
			name: "negative priority",
			cmd: CreateTaskCmd{
				RequestID:   "req-1",
				StoryID:     "story-1",
				Title:       "Task",
				Type:        "dev",
				Priority:    -1,
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "priority must be non-negative",
		},
		{
			name: "negative estimated hours",
			cmd: CreateTaskCmd{
				RequestID:      "req-1",
				StoryID:        "story-1",
				Title:          "Task",
				Type:           "dev",
				EstimatedHours: -1,
				RequestedBy:    "user-1",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "estimated hours must be non-negative",
		},
		{
			name: "planning client error",
			cmd: CreateTaskCmd{
				RequestID:   "req-1",
				StoryID:     "story-1",
				Title:       "Task",
				Type:        "dev",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{createTaskErr: errors.New("story not found")},
			wantErr:   true,
			errSubstr: "story not found",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			audit := &fakeAuditLogger{}
			handler := NewCreateTaskHandler(tt.planning, audit)

			taskID, err := handler.Handle(context.Background(), tt.cmd)

			if tt.wantErr {
				if err == nil {
					t.Fatalf("Handle() expected error containing %q, got nil", tt.errSubstr)
				}
				if !strings.Contains(err.Error(), tt.errSubstr) {
					t.Fatalf("Handle() error = %q, want substring %q", err.Error(), tt.errSubstr)
				}
				if len(audit.events) == 0 {
					t.Error("expected audit event on error, got none")
				}
				if len(audit.events) > 0 && audit.events[0].Success {
					t.Error("expected audit event Success=false on error")
				}
				return
			}

			if err != nil {
				t.Fatalf("Handle() unexpected error: %v", err)
			}

			if taskID != tt.wantID {
				t.Errorf("Handle() taskID = %q, want %q", taskID, tt.wantID)
			}

			if len(audit.events) == 0 {
				t.Fatal("expected audit event on success, got none")
			}
			if !audit.events[0].Success {
				t.Error("expected audit event Success=true on success")
			}
			if audit.events[0].Method != "CreateTask" {
				t.Errorf("audit Method = %q, want %q", audit.events[0].Method, "CreateTask")
			}
		})
	}
}

func TestCreateTaskCmd_Validate(t *testing.T) {
	t.Parallel()

	valid := CreateTaskCmd{
		RequestID:      "req-1",
		StoryID:        "story-1",
		Title:          "Task",
		Description:    "desc",
		Type:           "development",
		AssignedTo:     "agent-1",
		EstimatedHours: 4,
		Priority:       1,
		RequestedBy:    "user-1",
	}

	if err := valid.Validate(); err != nil {
		t.Errorf("valid command: Validate() = %v, want nil", err)
	}
}
