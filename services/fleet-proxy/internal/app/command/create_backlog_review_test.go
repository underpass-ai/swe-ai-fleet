package command

import (
	"context"
	"errors"
	"strings"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

func TestCreateBacklogReviewHandler_Handle(t *testing.T) {
	t.Parallel()

	sampleResult := ports.BacklogReviewResult{
		CeremonyID: "cer-abc",
		Status:     "DRAFT",
		CreatedBy:  "user-1",
	}

	tests := []struct {
		name      string
		cmd       CreateBacklogReviewCmd
		planning  *flexPlanningClient
		wantErr   bool
		errSubstr string
		wantCerID string
	}{
		{
			name: "successful creation",
			cmd: CreateBacklogReviewCmd{
				RequestID:   "req-1",
				RequestedBy: "user-1",
				StoryIDs:    []string{"story-1", "story-2"},
			},
			planning:  &flexPlanningClient{createBacklogReviewResult: sampleResult},
			wantCerID: "cer-abc",
		},
		{
			name: "empty request ID",
			cmd: CreateBacklogReviewCmd{
				RequestID:   "",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "request ID is required",
		},
		{
			name: "empty requestedBy",
			cmd: CreateBacklogReviewCmd{
				RequestID:   "req-1",
				RequestedBy: "",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "requestedBy is required",
		},
		{
			name: "planning client error",
			cmd: CreateBacklogReviewCmd{
				RequestID:   "req-1",
				RequestedBy: "user-1",
				StoryIDs:    []string{"story-1"},
			},
			planning:  &flexPlanningClient{createBacklogReviewErr: errors.New("upstream unavailable")},
			wantErr:   true,
			errSubstr: "upstream unavailable",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			audit := &fakeAuditLogger{}
			handler := NewCreateBacklogReviewHandler(tt.planning, audit)

			result, err := handler.Handle(context.Background(), tt.cmd)

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

			if result.CeremonyID != tt.wantCerID {
				t.Errorf("Handle() CeremonyID = %q, want %q", result.CeremonyID, tt.wantCerID)
			}

			if len(audit.events) == 0 {
				t.Fatal("expected audit event on success, got none")
			}
			if !audit.events[0].Success {
				t.Error("expected audit event Success=true on success")
			}
			if audit.events[0].Method != "CreateBacklogReview" {
				t.Errorf("audit Method = %q, want %q", audit.events[0].Method, "CreateBacklogReview")
			}
		})
	}
}

func TestCreateBacklogReviewCmd_Validate(t *testing.T) {
	t.Parallel()

	valid := CreateBacklogReviewCmd{
		RequestID:   "req-1",
		RequestedBy: "user-1",
		StoryIDs:    []string{"story-1"},
	}

	if err := valid.Validate(); err != nil {
		t.Errorf("valid command: Validate() = %v, want nil", err)
	}
}
