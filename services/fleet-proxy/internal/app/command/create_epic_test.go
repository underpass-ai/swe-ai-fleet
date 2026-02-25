package command

import (
	"context"
	"errors"
	"strings"
	"testing"
)

func TestCreateEpicHandler_Handle(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name      string
		cmd       CreateEpicCmd
		planning  *flexPlanningClient
		wantErr   bool
		errSubstr string
		wantID    string
	}{
		{
			name: "successful creation",
			cmd: CreateEpicCmd{
				RequestID:   "req-1",
				ProjectID:   "proj-1",
				Title:       "Epic Title",
				Description: "Epic description",
				RequestedBy: "user-1",
			},
			planning: &flexPlanningClient{createEpicID: "epic-abc"},
			wantID:   "epic-abc",
		},
		{
			name: "empty request ID",
			cmd: CreateEpicCmd{
				RequestID:   "",
				ProjectID:   "proj-1",
				Title:       "Epic",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "request ID is required",
		},
		{
			name: "empty project ID",
			cmd: CreateEpicCmd{
				RequestID:   "req-1",
				ProjectID:   "",
				Title:       "Epic",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "project ID is required",
		},
		{
			name: "empty title",
			cmd: CreateEpicCmd{
				RequestID:   "req-1",
				ProjectID:   "proj-1",
				Title:       "",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "epic title is required",
		},
		{
			name: "empty requestedBy",
			cmd: CreateEpicCmd{
				RequestID:   "req-1",
				ProjectID:   "proj-1",
				Title:       "Epic",
				RequestedBy: "",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "requestedBy is required",
		},
		{
			name: "planning client error",
			cmd: CreateEpicCmd{
				RequestID:   "req-1",
				ProjectID:   "proj-1",
				Title:       "Epic",
				Description: "desc",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{createEpicErr: errors.New("upstream timeout")},
			wantErr:   true,
			errSubstr: "upstream timeout",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			audit := &fakeAuditLogger{}
			handler := NewCreateEpicHandler(tt.planning, audit)

			epicID, err := handler.Handle(context.Background(), tt.cmd)

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

			if epicID != tt.wantID {
				t.Errorf("Handle() epicID = %q, want %q", epicID, tt.wantID)
			}

			if len(audit.events) == 0 {
				t.Fatal("expected audit event on success, got none")
			}
			if !audit.events[0].Success {
				t.Error("expected audit event Success=true on success")
			}
			if audit.events[0].Method != "CreateEpic" {
				t.Errorf("audit Method = %q, want %q", audit.events[0].Method, "CreateEpic")
			}
		})
	}
}

func TestCreateEpicCmd_Validate(t *testing.T) {
	t.Parallel()

	valid := CreateEpicCmd{
		RequestID:   "req-1",
		ProjectID:   "proj-1",
		Title:       "Epic",
		Description: "desc",
		RequestedBy: "user-1",
	}

	if err := valid.Validate(); err != nil {
		t.Errorf("valid command: Validate() = %v, want nil", err)
	}
}
