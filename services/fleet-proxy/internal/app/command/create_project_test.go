package command

import (
	"context"
	"errors"
	"strings"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

// ---------------------------------------------------------------------------
// Hand-written fake for PlanningClient
// ---------------------------------------------------------------------------

type fakePlanningClient struct {
	projectID string
	err       error
}

func (f *fakePlanningClient) CreateProject(_ context.Context, _, _ string) (string, error) {
	return f.projectID, f.err
}

func (f *fakePlanningClient) CreateEpic(_ context.Context, _, _, _ string) (string, error) {
	return "", nil
}

func (f *fakePlanningClient) CreateStory(_ context.Context, _, _, _ string) (string, error) {
	return "", nil
}

func (f *fakePlanningClient) TransitionStory(_ context.Context, _, _ string) error {
	return nil
}

func (f *fakePlanningClient) CreateTask(_ context.Context, _, _, _, _, _ string, _, _ int32) (string, error) {
	return "", nil
}

func (f *fakePlanningClient) ApproveDecision(_ context.Context, _, _, _ string) error {
	return nil
}

func (f *fakePlanningClient) RejectDecision(_ context.Context, _, _, _ string) error {
	return nil
}

func (f *fakePlanningClient) ListProjects(_ context.Context, _ string, _, _ int32) ([]ports.ProjectResult, int32, error) {
	return nil, 0, nil
}

func (f *fakePlanningClient) ListEpics(_ context.Context, _, _ string, _, _ int32) ([]ports.EpicResult, int32, error) {
	return nil, 0, nil
}

func (f *fakePlanningClient) ListStories(_ context.Context, _, _ string, _, _ int32) ([]ports.StoryResult, int32, error) {
	return nil, 0, nil
}

func (f *fakePlanningClient) ListTasks(_ context.Context, _, _ string, _, _ int32) ([]ports.TaskResult, int32, error) {
	return nil, 0, nil
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

func TestCreateProjectHandler_Handle(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name      string
		cmd       CreateProjectCmd
		planning  *fakePlanningClient
		wantErr   bool
		errSubstr string
		wantID    string
	}{
		{
			name: "successful creation",
			cmd: CreateProjectCmd{
				RequestID:   "req-1",
				Name:        "My Project",
				Description: "A cool project",
				RequestedBy: "spiffe://swe-ai-fleet/user/tirso/device/macbook",
			},
			planning: &fakePlanningClient{projectID: "proj-abc"},
			wantID:   "proj-abc",
		},
		{
			name: "empty name",
			cmd: CreateProjectCmd{
				RequestID:   "req-2",
				Name:        "",
				Description: "desc",
				RequestedBy: "user-1",
			},
			planning:  &fakePlanningClient{},
			wantErr:   true,
			errSubstr: "project name is required",
		},
		{
			name: "empty request ID",
			cmd: CreateProjectCmd{
				RequestID:   "",
				Name:        "project",
				Description: "desc",
				RequestedBy: "user-1",
			},
			planning:  &fakePlanningClient{},
			wantErr:   true,
			errSubstr: "request ID is required",
		},
		{
			name: "empty requestedBy",
			cmd: CreateProjectCmd{
				RequestID:   "req-3",
				Name:        "project",
				Description: "desc",
				RequestedBy: "",
			},
			planning:  &fakePlanningClient{},
			wantErr:   true,
			errSubstr: "requestedBy is required",
		},
		{
			name: "planning client returns error",
			cmd: CreateProjectCmd{
				RequestID:   "req-4",
				Name:        "project",
				Description: "desc",
				RequestedBy: "user-1",
			},
			planning:  &fakePlanningClient{err: errors.New("upstream unavailable")},
			wantErr:   true,
			errSubstr: "upstream unavailable",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			audit := &fakeAuditLogger{}
			handler := NewCreateProjectHandler(tt.planning, audit)

			projectID, err := handler.Handle(context.Background(), tt.cmd)

			if tt.wantErr {
				if err == nil {
					t.Fatalf("Handle() expected error containing %q, got nil", tt.errSubstr)
				}
				if !strings.Contains(err.Error(), tt.errSubstr) {
					t.Fatalf("Handle() error = %q, want substring %q", err.Error(), tt.errSubstr)
				}
				// Verify audit was recorded on error.
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

			if projectID != tt.wantID {
				t.Errorf("Handle() projectID = %q, want %q", projectID, tt.wantID)
			}

			// Verify audit was recorded on success.
			if len(audit.events) == 0 {
				t.Fatal("expected audit event on success, got none")
			}
			if !audit.events[0].Success {
				t.Error("expected audit event Success=true on success")
			}
			if audit.events[0].Method != "CreateProject" {
				t.Errorf("audit Method = %q, want %q", audit.events[0].Method, "CreateProject")
			}
			if audit.events[0].ClientID != tt.cmd.RequestedBy {
				t.Errorf("audit ClientID = %q, want %q", audit.events[0].ClientID, tt.cmd.RequestedBy)
			}
		})
	}
}

func TestCreateProjectCmd_Validate(t *testing.T) {
	t.Parallel()

	valid := CreateProjectCmd{
		RequestID:   "req-1",
		Name:        "project",
		Description: "desc",
		RequestedBy: "user-1",
	}

	if err := valid.Validate(); err != nil {
		t.Errorf("valid command: Validate() = %v, want nil", err)
	}
}
