package command

import (
	"context"
	"errors"
	"strings"
	"testing"
)

func TestStartBacklogReviewHandler_Handle(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name      string
		cmd       StartBacklogReviewCmd
		ceremony  *flexCeremonyClient
		wantErr   bool
		errSubstr string
		wantCount int32
	}{
		{
			name: "successful start",
			cmd: StartBacklogReviewCmd{
				RequestID:   "req-1",
				CeremonyID:  "cer-1",
				RequestedBy: "user-1",
			},
			ceremony:  &flexCeremonyClient{startBacklogReviewCount: 5},
			wantCount: 5,
		},
		{
			name: "empty request ID",
			cmd: StartBacklogReviewCmd{
				RequestID:   "",
				CeremonyID:  "cer-1",
				RequestedBy: "user-1",
			},
			ceremony:  &flexCeremonyClient{},
			wantErr:   true,
			errSubstr: "request ID is required",
		},
		{
			name: "empty ceremony ID",
			cmd: StartBacklogReviewCmd{
				RequestID:   "req-1",
				CeremonyID:  "",
				RequestedBy: "user-1",
			},
			ceremony:  &flexCeremonyClient{},
			wantErr:   true,
			errSubstr: "ceremony ID is required",
		},
		{
			name: "empty requestedBy",
			cmd: StartBacklogReviewCmd{
				RequestID:   "req-1",
				CeremonyID:  "cer-1",
				RequestedBy: "",
			},
			ceremony:  &flexCeremonyClient{},
			wantErr:   true,
			errSubstr: "requestedBy is required",
		},
		{
			name: "ceremony client error",
			cmd: StartBacklogReviewCmd{
				RequestID:   "req-1",
				CeremonyID:  "cer-1",
				RequestedBy: "user-1",
			},
			ceremony:  &flexCeremonyClient{startBacklogReviewErr: errors.New("review already in progress")},
			wantErr:   true,
			errSubstr: "review already in progress",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			audit := &fakeAuditLogger{}
			handler := NewStartBacklogReviewHandler(tt.ceremony, audit)

			count, err := handler.Handle(context.Background(), tt.cmd)

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

			if count != tt.wantCount {
				t.Errorf("Handle() count = %d, want %d", count, tt.wantCount)
			}

			if len(audit.events) == 0 {
				t.Fatal("expected audit event on success, got none")
			}
			if !audit.events[0].Success {
				t.Error("expected audit event Success=true on success")
			}
			if audit.events[0].Method != "StartBacklogReview" {
				t.Errorf("audit Method = %q, want %q", audit.events[0].Method, "StartBacklogReview")
			}
		})
	}
}

func TestStartBacklogReviewCmd_Validate(t *testing.T) {
	t.Parallel()

	valid := StartBacklogReviewCmd{
		RequestID:   "req-1",
		CeremonyID:  "cer-1",
		RequestedBy: "user-1",
	}

	if err := valid.Validate(); err != nil {
		t.Errorf("valid command: Validate() = %v, want nil", err)
	}
}
