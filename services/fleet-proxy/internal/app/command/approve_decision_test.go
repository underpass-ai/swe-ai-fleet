package command

import (
	"context"
	"errors"
	"strings"
	"testing"
)

func TestApproveDecisionHandler_Handle(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name      string
		cmd       ApproveDecisionCmd
		planning  *flexPlanningClient
		wantErr   bool
		errSubstr string
	}{
		{
			name: "successful approval",
			cmd: ApproveDecisionCmd{
				StoryID:     "story-1",
				DecisionID:  "dec-1",
				Comment:     "Looks good",
				RequestedBy: "user-1",
			},
			planning: &flexPlanningClient{},
		},
		{
			name: "successful approval without comment",
			cmd: ApproveDecisionCmd{
				StoryID:     "story-1",
				DecisionID:  "dec-1",
				Comment:     "",
				RequestedBy: "user-1",
			},
			planning: &flexPlanningClient{},
		},
		{
			name: "empty story ID",
			cmd: ApproveDecisionCmd{
				StoryID:     "",
				DecisionID:  "dec-1",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "story ID is required",
		},
		{
			name: "empty decision ID",
			cmd: ApproveDecisionCmd{
				StoryID:     "story-1",
				DecisionID:  "",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "decision ID is required",
		},
		{
			name: "empty requestedBy",
			cmd: ApproveDecisionCmd{
				StoryID:     "story-1",
				DecisionID:  "dec-1",
				RequestedBy: "",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "requestedBy is required",
		},
		{
			name: "planning client error",
			cmd: ApproveDecisionCmd{
				StoryID:     "story-1",
				DecisionID:  "dec-1",
				Comment:     "ok",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{approveDecisionErr: errors.New("decision not found")},
			wantErr:   true,
			errSubstr: "decision not found",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			audit := &fakeAuditLogger{}
			handler := NewApproveDecisionHandler(tt.planning, audit)

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
			if audit.events[0].Method != "ApproveDecision" {
				t.Errorf("audit Method = %q, want %q", audit.events[0].Method, "ApproveDecision")
			}
		})
	}
}

func TestApproveDecisionCmd_Validate(t *testing.T) {
	t.Parallel()

	valid := ApproveDecisionCmd{
		StoryID:     "story-1",
		DecisionID:  "dec-1",
		Comment:     "ok",
		RequestedBy: "user-1",
	}

	if err := valid.Validate(); err != nil {
		t.Errorf("valid command: Validate() = %v, want nil", err)
	}
}
