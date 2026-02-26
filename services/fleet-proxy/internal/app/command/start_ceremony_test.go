package command

import (
	"context"
	"errors"
	"strings"
	"testing"
)

func TestStartCeremonyHandler_Handle(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name      string
		cmd       StartCeremonyCmd
		ceremony  *flexCeremonyClient
		wantErr   bool
		errSubstr string
		wantID    string
	}{
		{
			name: "successful start",
			cmd: StartCeremonyCmd{
				RequestID:      "req-1",
				CeremonyID:     "cer-1",
				DefinitionName: "planning",
				StoryID:        "story-1",
				StepIDs:        []string{"step-1", "step-2"},
				RequestedBy:    "user-1",
			},
			ceremony: &flexCeremonyClient{startCeremonyID: "instance-abc"},
			wantID:   "instance-abc",
		},
		{
			name: "empty request ID",
			cmd: StartCeremonyCmd{
				RequestID:      "",
				CeremonyID:     "cer-1",
				DefinitionName: "planning",
				StoryID:        "story-1",
				StepIDs:        []string{"step-1"},
				RequestedBy:    "user-1",
			},
			ceremony:  &flexCeremonyClient{},
			wantErr:   true,
			errSubstr: "request ID is required",
		},
		{
			name: "empty ceremony ID",
			cmd: StartCeremonyCmd{
				RequestID:      "req-1",
				CeremonyID:     "",
				DefinitionName: "planning",
				StoryID:        "story-1",
				StepIDs:        []string{"step-1"},
				RequestedBy:    "user-1",
			},
			ceremony:  &flexCeremonyClient{},
			wantErr:   true,
			errSubstr: "ceremony ID is required",
		},
		{
			name: "empty definition name",
			cmd: StartCeremonyCmd{
				RequestID:      "req-1",
				CeremonyID:     "cer-1",
				DefinitionName: "",
				StoryID:        "story-1",
				StepIDs:        []string{"step-1"},
				RequestedBy:    "user-1",
			},
			ceremony:  &flexCeremonyClient{},
			wantErr:   true,
			errSubstr: "definition name is required",
		},
		{
			name: "empty story ID",
			cmd: StartCeremonyCmd{
				RequestID:      "req-1",
				CeremonyID:     "cer-1",
				DefinitionName: "planning",
				StoryID:        "",
				StepIDs:        []string{"step-1"},
				RequestedBy:    "user-1",
			},
			ceremony:  &flexCeremonyClient{},
			wantErr:   true,
			errSubstr: "story ID is required",
		},
		{
			name: "empty step IDs",
			cmd: StartCeremonyCmd{
				RequestID:      "req-1",
				CeremonyID:     "cer-1",
				DefinitionName: "planning",
				StoryID:        "story-1",
				StepIDs:        []string{},
				RequestedBy:    "user-1",
			},
			ceremony:  &flexCeremonyClient{},
			wantErr:   true,
			errSubstr: "at least one step ID is required",
		},
		{
			name: "nil step IDs",
			cmd: StartCeremonyCmd{
				RequestID:      "req-1",
				CeremonyID:     "cer-1",
				DefinitionName: "planning",
				StoryID:        "story-1",
				StepIDs:        nil,
				RequestedBy:    "user-1",
			},
			ceremony:  &flexCeremonyClient{},
			wantErr:   true,
			errSubstr: "at least one step ID is required",
		},
		{
			name: "empty requestedBy",
			cmd: StartCeremonyCmd{
				RequestID:      "req-1",
				CeremonyID:     "cer-1",
				DefinitionName: "planning",
				StoryID:        "story-1",
				StepIDs:        []string{"step-1"},
				RequestedBy:    "",
			},
			ceremony:  &flexCeremonyClient{},
			wantErr:   true,
			errSubstr: "requestedBy is required",
		},
		{
			name: "ceremony client error",
			cmd: StartCeremonyCmd{
				RequestID:      "req-1",
				CeremonyID:     "cer-1",
				DefinitionName: "planning",
				StoryID:        "story-1",
				StepIDs:        []string{"step-1"},
				RequestedBy:    "user-1",
			},
			ceremony:  &flexCeremonyClient{startCeremonyErr: errors.New("ceremony service unavailable")},
			wantErr:   true,
			errSubstr: "ceremony service unavailable",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			audit := &fakeAuditLogger{}
			handler := NewStartCeremonyHandler(tt.ceremony, audit)

			instanceID, err := handler.Handle(context.Background(), tt.cmd)

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

			if instanceID != tt.wantID {
				t.Errorf("Handle() instanceID = %q, want %q", instanceID, tt.wantID)
			}

			if len(audit.events) == 0 {
				t.Fatal("expected audit event on success, got none")
			}
			if !audit.events[0].Success {
				t.Error("expected audit event Success=true on success")
			}
			if audit.events[0].Method != "StartCeremony" {
				t.Errorf("audit Method = %q, want %q", audit.events[0].Method, "StartCeremony")
			}
		})
	}
}

func TestStartCeremonyCmd_Validate(t *testing.T) {
	t.Parallel()

	valid := StartCeremonyCmd{
		RequestID:      "req-1",
		CeremonyID:     "cer-1",
		DefinitionName: "planning",
		StoryID:        "story-1",
		StepIDs:        []string{"step-1"},
		RequestedBy:    "user-1",
	}

	if err := valid.Validate(); err != nil {
		t.Errorf("valid command: Validate() = %v, want nil", err)
	}
}
