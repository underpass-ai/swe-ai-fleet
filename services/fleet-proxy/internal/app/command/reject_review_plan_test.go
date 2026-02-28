package command

import (
	"context"
	"errors"
	"strings"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

func TestRejectReviewPlanHandler_Handle(t *testing.T) {
	t.Parallel()

	sampleResult := ports.BacklogReviewResult{
		CeremonyID: "cer-1",
		Status:     "REVIEWING",
	}

	tests := []struct {
		name      string
		cmd       RejectReviewPlanCmd
		planning  *flexPlanningClient
		wantErr   bool
		errSubstr string
		wantCerID string
	}{
		{
			name: "successful rejection",
			cmd: RejectReviewPlanCmd{
				RequestID:   "req-1",
				CeremonyID:  "cer-1",
				StoryID:     "story-1",
				Reason:      "Needs more technical detail",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{rejectReviewPlanResult: sampleResult},
			wantCerID: "cer-1",
		},
		{
			name: "empty request ID",
			cmd: RejectReviewPlanCmd{
				RequestID:   "",
				CeremonyID:  "cer-1",
				StoryID:     "story-1",
				Reason:      "reason",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "request ID is required",
		},
		{
			name: "empty ceremony ID",
			cmd: RejectReviewPlanCmd{
				RequestID:   "req-1",
				CeremonyID:  "",
				StoryID:     "story-1",
				Reason:      "reason",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "ceremony ID is required",
		},
		{
			name: "empty story ID",
			cmd: RejectReviewPlanCmd{
				RequestID:   "req-1",
				CeremonyID:  "cer-1",
				StoryID:     "",
				Reason:      "reason",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "story ID is required",
		},
		{
			name: "empty reason",
			cmd: RejectReviewPlanCmd{
				RequestID:   "req-1",
				CeremonyID:  "cer-1",
				StoryID:     "story-1",
				Reason:      "",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "rejection reason is required",
		},
		{
			name: "empty requestedBy",
			cmd: RejectReviewPlanCmd{
				RequestID:   "req-1",
				CeremonyID:  "cer-1",
				StoryID:     "story-1",
				Reason:      "reason",
				RequestedBy: "",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "requestedBy is required",
		},
		{
			name: "planning client error",
			cmd: RejectReviewPlanCmd{
				RequestID:   "req-1",
				CeremonyID:  "cer-1",
				StoryID:     "story-1",
				Reason:      "reason",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{rejectReviewPlanErr: errors.New("story not found")},
			wantErr:   true,
			errSubstr: "story not found",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			audit := &fakeAuditLogger{}
			handler := NewRejectReviewPlanHandler(tt.planning, audit)

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
			if audit.events[0].Method != "RejectReviewPlan" {
				t.Errorf("audit Method = %q, want %q", audit.events[0].Method, "RejectReviewPlan")
			}
		})
	}
}

func TestRejectReviewPlanCmd_Validate(t *testing.T) {
	t.Parallel()

	valid := RejectReviewPlanCmd{
		RequestID:   "req-1",
		CeremonyID:  "cer-1",
		StoryID:     "story-1",
		Reason:      "not ready",
		RequestedBy: "user-1",
	}

	if err := valid.Validate(); err != nil {
		t.Errorf("valid command: Validate() = %v, want nil", err)
	}
}
