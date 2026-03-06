package command

import (
	"context"
	"errors"
	"strings"
	"testing"
)

func TestRejectDecisionHandler_Handle(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name      string
		cmd       RejectDecisionCmd
		planning  *flexPlanningClient
		wantErr   bool
		errSubstr string
	}{
		{
			name: "successful rejection",
			cmd: RejectDecisionCmd{
				StoryID:     "story-1",
				DecisionID:  "dec-1",
				Reason:      "Does not meet criteria",
				RequestedBy: "user-1",
			},
			planning: &flexPlanningClient{},
		},
		{
			name: "empty story ID",
			cmd: RejectDecisionCmd{
				StoryID:     "",
				DecisionID:  "dec-1",
				Reason:      "reason",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "story ID is required",
		},
		{
			name: "empty decision ID",
			cmd: RejectDecisionCmd{
				StoryID:     "story-1",
				DecisionID:  "",
				Reason:      "reason",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "decision ID is required",
		},
		{
			name: "empty reason",
			cmd: RejectDecisionCmd{
				StoryID:     "story-1",
				DecisionID:  "dec-1",
				Reason:      "",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "rejection reason is required",
		},
		{
			name: "empty requestedBy",
			cmd: RejectDecisionCmd{
				StoryID:     "story-1",
				DecisionID:  "dec-1",
				Reason:      "reason",
				RequestedBy: "",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "requestedBy is required",
		},
		{
			name: "planning client error",
			cmd: RejectDecisionCmd{
				StoryID:     "story-1",
				DecisionID:  "dec-1",
				Reason:      "bad",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{rejectDecisionErr: errors.New("decision already resolved")},
			wantErr:   true,
			errSubstr: "decision already resolved",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			audit := &fakeAuditLogger{}
			handler := NewRejectDecisionHandler(tt.planning, audit)

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
			if audit.events[0].Method != "RejectDecision" {
				t.Errorf("audit Method = %q, want %q", audit.events[0].Method, "RejectDecision")
			}
		})
	}
}

func TestRejectDecisionCmd_Validate(t *testing.T) {
	t.Parallel()

	valid := RejectDecisionCmd{
		StoryID:     "story-1",
		DecisionID:  "dec-1",
		Reason:      "not ready",
		RequestedBy: "user-1",
	}

	if err := valid.Validate(); err != nil {
		t.Errorf("valid command: Validate() = %v, want nil", err)
	}
}
