package command

import (
	"context"
	"errors"
	"strings"
	"testing"
)

func TestTransitionStoryHandler_Handle(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name      string
		cmd       TransitionStoryCmd
		planning  *flexPlanningClient
		wantErr   bool
		errSubstr string
	}{
		{
			name: "successful transition",
			cmd: TransitionStoryCmd{
				StoryID:     "story-1",
				TargetState: "in_progress",
				RequestedBy: "user-1",
			},
			planning: &flexPlanningClient{},
		},
		{
			name: "empty story ID",
			cmd: TransitionStoryCmd{
				StoryID:     "",
				TargetState: "in_progress",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "story ID is required",
		},
		{
			name: "empty target state",
			cmd: TransitionStoryCmd{
				StoryID:     "story-1",
				TargetState: "",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "target state is required",
		},
		{
			name: "empty requestedBy",
			cmd: TransitionStoryCmd{
				StoryID:     "story-1",
				TargetState: "in_progress",
				RequestedBy: "",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "requestedBy is required",
		},
		{
			name: "planning client error",
			cmd: TransitionStoryCmd{
				StoryID:     "story-1",
				TargetState: "done",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{transitionStoryErr: errors.New("invalid transition")},
			wantErr:   true,
			errSubstr: "invalid transition",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			audit := &fakeAuditLogger{}
			handler := NewTransitionStoryHandler(tt.planning, audit)

			err := handler.Handle(context.Background(), tt.cmd)

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

			if len(audit.events) == 0 {
				t.Fatal("expected audit event on success, got none")
			}
			if !audit.events[0].Success {
				t.Error("expected audit event Success=true on success")
			}
			if audit.events[0].Method != "TransitionStory" {
				t.Errorf("audit Method = %q, want %q", audit.events[0].Method, "TransitionStory")
			}
		})
	}
}

func TestTransitionStoryCmd_Validate(t *testing.T) {
	t.Parallel()

	valid := TransitionStoryCmd{
		StoryID:     "story-1",
		TargetState: "in_progress",
		RequestedBy: "user-1",
	}

	if err := valid.Validate(); err != nil {
		t.Errorf("valid command: Validate() = %v, want nil", err)
	}
}
