package command

import (
	"context"
	"errors"
	"strings"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

func TestApproveReviewPlanHandler_Handle(t *testing.T) {
	t.Parallel()

	sampleResult := ports.BacklogReviewResult{
		CeremonyID: "cer-1",
		Status:     "REVIEWING",
	}

	tests := []struct {
		name       string
		cmd        ApproveReviewPlanCmd
		planning   *flexPlanningClient
		wantErr    bool
		errSubstr  string
		wantPlanID string
	}{
		{
			name: "successful approval",
			cmd: ApproveReviewPlanCmd{
				RequestID:   "req-1",
				CeremonyID:  "cer-1",
				StoryID:     "story-1",
				PONotes:     "Looks good, approved for implementation",
				RequestedBy: "user-1",
			},
			planning:   &flexPlanningClient{approveReviewPlanResult: sampleResult, approveReviewPlanID: "plan-xyz"},
			wantPlanID: "plan-xyz",
		},
		{
			name: "empty request ID",
			cmd: ApproveReviewPlanCmd{
				RequestID:   "",
				CeremonyID:  "cer-1",
				StoryID:     "story-1",
				PONotes:     "notes",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "request ID is required",
		},
		{
			name: "empty ceremony ID",
			cmd: ApproveReviewPlanCmd{
				RequestID:   "req-1",
				CeremonyID:  "",
				StoryID:     "story-1",
				PONotes:     "notes",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "ceremony ID is required",
		},
		{
			name: "empty story ID",
			cmd: ApproveReviewPlanCmd{
				RequestID:   "req-1",
				CeremonyID:  "cer-1",
				StoryID:     "",
				PONotes:     "notes",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "story ID is required",
		},
		{
			name: "empty PO notes",
			cmd: ApproveReviewPlanCmd{
				RequestID:   "req-1",
				CeremonyID:  "cer-1",
				StoryID:     "story-1",
				PONotes:     "",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "PO notes are required",
		},
		{
			name: "empty requestedBy",
			cmd: ApproveReviewPlanCmd{
				RequestID:   "req-1",
				CeremonyID:  "cer-1",
				StoryID:     "story-1",
				PONotes:     "notes",
				RequestedBy: "",
			},
			planning:  &flexPlanningClient{},
			wantErr:   true,
			errSubstr: "requestedBy is required",
		},
		{
			name: "planning client error",
			cmd: ApproveReviewPlanCmd{
				RequestID:   "req-1",
				CeremonyID:  "cer-1",
				StoryID:     "story-1",
				PONotes:     "notes",
				RequestedBy: "user-1",
			},
			planning:  &flexPlanningClient{approveReviewPlanErr: errors.New("story not found")},
			wantErr:   true,
			errSubstr: "story not found",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			audit := &fakeAuditLogger{}
			handler := NewApproveReviewPlanHandler(tt.planning, audit)

			result, planID, err := handler.Handle(context.Background(), tt.cmd)

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

			if planID != tt.wantPlanID {
				t.Errorf("Handle() planID = %q, want %q", planID, tt.wantPlanID)
			}

			if result.CeremonyID != "cer-1" {
				t.Errorf("Handle() CeremonyID = %q, want %q", result.CeremonyID, "cer-1")
			}

			if len(audit.events) == 0 {
				t.Fatal("expected audit event on success, got none")
			}
			if !audit.events[0].Success {
				t.Error("expected audit event Success=true on success")
			}
			if audit.events[0].Method != "ApproveReviewPlan" {
				t.Errorf("audit Method = %q, want %q", audit.events[0].Method, "ApproveReviewPlan")
			}
		})
	}
}

func TestApproveReviewPlanCmd_Validate(t *testing.T) {
	t.Parallel()

	valid := ApproveReviewPlanCmd{
		RequestID:   "req-1",
		CeremonyID:  "cer-1",
		StoryID:     "story-1",
		PONotes:     "approved",
		RequestedBy: "user-1",
	}

	if err := valid.Validate(); err != nil {
		t.Errorf("valid command: Validate() = %v, want nil", err)
	}
}
