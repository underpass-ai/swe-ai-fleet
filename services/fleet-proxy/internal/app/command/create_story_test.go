package command

import (
	"context"
	"errors"
	"strings"
	"testing"
)

func TestCreateStoryHandler_Handle(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name      string
		cmd       CreateStoryCmd
		planning  *flexPlanningClient
		wantErr   bool
		errSubstr string
		wantID    string
	}{
		{
			name: "successful creation",
			cmd: CreateStoryCmd{
				RequestID:   "req-1",
				EpicID:      "epic-1",
				Title:       "Story Title",
				Brief:       "Story brief",
				RequestedBy: "user-1",
			},
			planning: &flexPlanningClient{createStoryID: "story-abc"},
			wantID:   "story-abc",
		},
		{
			name: "empty request ID",
			cmd: CreateStoryCmd{
				RequestID:   "",
				EpicID:      "epic-1",
				Title:       "Story",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "request ID is required",
		},
		{
			name: "empty epic ID",
			cmd: CreateStoryCmd{
				RequestID:   "req-1",
				EpicID:      "",
				Title:       "Story",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "epic ID is required",
		},
		{
			name: "empty title",
			cmd: CreateStoryCmd{
				RequestID:   "req-1",
				EpicID:      "epic-1",
				Title:       "",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "story title is required",
		},
		{
			name: "empty requestedBy",
			cmd: CreateStoryCmd{
				RequestID:   "req-1",
				EpicID:      "epic-1",
				Title:       "Story",
				RequestedBy: "",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "requestedBy is required",
		},
		{
			name: "planning client error",
			cmd: CreateStoryCmd{
				RequestID:   "req-1",
				EpicID:      "epic-1",
				Title:       "Story",
				Brief:       "brief",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{createStoryErr: errors.New("connection refused")},
			wantErr:   true,
			errSubstr: "connection refused",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			audit := &fakeAuditLogger{}
			handler := NewCreateStoryHandler(tt.planning, audit)

			storyID, err := handler.Handle(context.Background(), tt.cmd)

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

			if storyID != tt.wantID {
				t.Errorf("Handle() storyID = %q, want %q", storyID, tt.wantID)
			}

			if len(audit.events) == 0 {
				t.Fatal("expected audit event on success, got none")
			}
			if !audit.events[0].Success {
				t.Error("expected audit event Success=true on success")
			}
			if audit.events[0].Method != "CreateStory" {
				t.Errorf("audit Method = %q, want %q", audit.events[0].Method, "CreateStory")
			}
		})
	}
}

func TestCreateStoryCmd_Validate(t *testing.T) {
	t.Parallel()

	valid := CreateStoryCmd{
		RequestID:   "req-1",
		EpicID:      "epic-1",
		Title:       "Story",
		Brief:       "brief",
		RequestedBy: "user-1",
	}

	if err := valid.Validate(); err != nil {
		t.Errorf("valid command: Validate() = %v, want nil", err)
	}
}
