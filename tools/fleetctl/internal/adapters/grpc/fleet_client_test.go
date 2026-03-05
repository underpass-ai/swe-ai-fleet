package grpc

import (
	"context"
	"net"
	"strings"
	"testing"

	proxyv1 "github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/gen/proxyv1"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/status"
	"google.golang.org/grpc/test/bufconn"
)

const testBufSize = 1 << 20

// ---------------------------------------------------------------------------
// fakeCommandServer
// ---------------------------------------------------------------------------

type fakeCommandServer struct {
	proxyv1.UnimplementedFleetCommandServiceServer

	createProjectResp *proxyv1.CreateProjectResponse
	createProjectErr  error

	createEpicResp *proxyv1.CreateEpicResponse
	createEpicErr  error

	createStoryResp *proxyv1.CreateStoryResponse
	createStoryErr  error

	transitionStoryResp *proxyv1.TransitionStoryResponse
	transitionStoryErr  error

	startCeremonyResp *proxyv1.StartPlanningCeremonyResponse
	startCeremonyErr  error

	createTaskResp *proxyv1.CreateTaskResponse
	createTaskErr  error

	approveDecisionResp *proxyv1.ApproveDecisionResponse
	approveDecisionErr  error

	rejectDecisionResp *proxyv1.RejectDecisionResponse
	rejectDecisionErr  error

	createBacklogReviewResp *proxyv1.CreateBacklogReviewResponse
	createBacklogReviewErr  error

	startBacklogReviewResp *proxyv1.StartBacklogReviewResponse
	startBacklogReviewErr  error

	approveReviewPlanResp *proxyv1.ApproveReviewPlanResponse
	approveReviewPlanErr  error

	rejectReviewPlanResp *proxyv1.RejectReviewPlanResponse
	rejectReviewPlanErr  error

	completeBacklogReviewResp *proxyv1.CompleteBacklogReviewResponse
	completeBacklogReviewErr  error

	cancelBacklogReviewResp *proxyv1.CancelBacklogReviewResponse
	cancelBacklogReviewErr  error
}

func (f *fakeCommandServer) CreateProject(_ context.Context, _ *proxyv1.CreateProjectRequest) (*proxyv1.CreateProjectResponse, error) {
	if f.createProjectErr != nil {
		return nil, f.createProjectErr
	}
	return f.createProjectResp, nil
}

func (f *fakeCommandServer) CreateEpic(_ context.Context, _ *proxyv1.CreateEpicRequest) (*proxyv1.CreateEpicResponse, error) {
	if f.createEpicErr != nil {
		return nil, f.createEpicErr
	}
	return f.createEpicResp, nil
}

func (f *fakeCommandServer) CreateStory(_ context.Context, _ *proxyv1.CreateStoryRequest) (*proxyv1.CreateStoryResponse, error) {
	if f.createStoryErr != nil {
		return nil, f.createStoryErr
	}
	return f.createStoryResp, nil
}

func (f *fakeCommandServer) TransitionStory(_ context.Context, _ *proxyv1.TransitionStoryRequest) (*proxyv1.TransitionStoryResponse, error) {
	if f.transitionStoryErr != nil {
		return nil, f.transitionStoryErr
	}
	return f.transitionStoryResp, nil
}

func (f *fakeCommandServer) StartPlanningCeremony(_ context.Context, _ *proxyv1.StartPlanningCeremonyRequest) (*proxyv1.StartPlanningCeremonyResponse, error) {
	if f.startCeremonyErr != nil {
		return nil, f.startCeremonyErr
	}
	return f.startCeremonyResp, nil
}

func (f *fakeCommandServer) CreateTask(_ context.Context, _ *proxyv1.CreateTaskRequest) (*proxyv1.CreateTaskResponse, error) {
	if f.createTaskErr != nil {
		return nil, f.createTaskErr
	}
	return f.createTaskResp, nil
}

func (f *fakeCommandServer) ApproveDecision(_ context.Context, _ *proxyv1.ApproveDecisionRequest) (*proxyv1.ApproveDecisionResponse, error) {
	if f.approveDecisionErr != nil {
		return nil, f.approveDecisionErr
	}
	return f.approveDecisionResp, nil
}

func (f *fakeCommandServer) RejectDecision(_ context.Context, _ *proxyv1.RejectDecisionRequest) (*proxyv1.RejectDecisionResponse, error) {
	if f.rejectDecisionErr != nil {
		return nil, f.rejectDecisionErr
	}
	return f.rejectDecisionResp, nil
}

func (f *fakeCommandServer) CreateBacklogReview(_ context.Context, _ *proxyv1.CreateBacklogReviewRequest) (*proxyv1.CreateBacklogReviewResponse, error) {
	if f.createBacklogReviewErr != nil {
		return nil, f.createBacklogReviewErr
	}
	return f.createBacklogReviewResp, nil
}

func (f *fakeCommandServer) StartBacklogReview(_ context.Context, _ *proxyv1.StartBacklogReviewRequest) (*proxyv1.StartBacklogReviewResponse, error) {
	if f.startBacklogReviewErr != nil {
		return nil, f.startBacklogReviewErr
	}
	return f.startBacklogReviewResp, nil
}

func (f *fakeCommandServer) ApproveReviewPlan(_ context.Context, _ *proxyv1.ApproveReviewPlanRequest) (*proxyv1.ApproveReviewPlanResponse, error) {
	if f.approveReviewPlanErr != nil {
		return nil, f.approveReviewPlanErr
	}
	return f.approveReviewPlanResp, nil
}

func (f *fakeCommandServer) RejectReviewPlan(_ context.Context, _ *proxyv1.RejectReviewPlanRequest) (*proxyv1.RejectReviewPlanResponse, error) {
	if f.rejectReviewPlanErr != nil {
		return nil, f.rejectReviewPlanErr
	}
	return f.rejectReviewPlanResp, nil
}

func (f *fakeCommandServer) CompleteBacklogReview(_ context.Context, _ *proxyv1.CompleteBacklogReviewRequest) (*proxyv1.CompleteBacklogReviewResponse, error) {
	if f.completeBacklogReviewErr != nil {
		return nil, f.completeBacklogReviewErr
	}
	return f.completeBacklogReviewResp, nil
}

func (f *fakeCommandServer) CancelBacklogReview(_ context.Context, _ *proxyv1.CancelBacklogReviewRequest) (*proxyv1.CancelBacklogReviewResponse, error) {
	if f.cancelBacklogReviewErr != nil {
		return nil, f.cancelBacklogReviewErr
	}
	return f.cancelBacklogReviewResp, nil
}

// ---------------------------------------------------------------------------
// fakeQueryServer
// ---------------------------------------------------------------------------

type fakeQueryServer struct {
	proxyv1.UnimplementedFleetQueryServiceServer

	listProjectsResp *proxyv1.ListProjectsResponse
	listProjectsErr  error

	listEpicsResp *proxyv1.ListEpicsResponse
	listEpicsErr  error

	listStoriesResp *proxyv1.ListStoriesResponse
	listStoriesErr  error

	listTasksResp *proxyv1.ListTasksResponse
	listTasksErr  error

	listCeremonyInstancesResp *proxyv1.ListCeremonyInstancesResponse
	listCeremonyInstancesErr  error

	getCeremonyInstanceResp *proxyv1.CeremonyInstanceResponse
	getCeremonyInstanceErr  error

	getBacklogReviewResp *proxyv1.GetBacklogReviewResponse
	getBacklogReviewErr  error

	listBacklogReviewsResp *proxyv1.ListBacklogReviewsResponse
	listBacklogReviewsErr  error
}

func (f *fakeQueryServer) ListProjects(_ context.Context, _ *proxyv1.ListProjectsRequest) (*proxyv1.ListProjectsResponse, error) {
	if f.listProjectsErr != nil {
		return nil, f.listProjectsErr
	}
	return f.listProjectsResp, nil
}

func (f *fakeQueryServer) ListEpics(_ context.Context, _ *proxyv1.ListEpicsRequest) (*proxyv1.ListEpicsResponse, error) {
	if f.listEpicsErr != nil {
		return nil, f.listEpicsErr
	}
	return f.listEpicsResp, nil
}

func (f *fakeQueryServer) ListStories(_ context.Context, _ *proxyv1.ListStoriesRequest) (*proxyv1.ListStoriesResponse, error) {
	if f.listStoriesErr != nil {
		return nil, f.listStoriesErr
	}
	return f.listStoriesResp, nil
}

func (f *fakeQueryServer) ListTasks(_ context.Context, _ *proxyv1.ListTasksRequest) (*proxyv1.ListTasksResponse, error) {
	if f.listTasksErr != nil {
		return nil, f.listTasksErr
	}
	return f.listTasksResp, nil
}

func (f *fakeQueryServer) ListCeremonyInstances(_ context.Context, _ *proxyv1.ListCeremonyInstancesRequest) (*proxyv1.ListCeremonyInstancesResponse, error) {
	if f.listCeremonyInstancesErr != nil {
		return nil, f.listCeremonyInstancesErr
	}
	return f.listCeremonyInstancesResp, nil
}

func (f *fakeQueryServer) GetCeremonyInstance(_ context.Context, _ *proxyv1.GetCeremonyInstanceRequest) (*proxyv1.CeremonyInstanceResponse, error) {
	if f.getCeremonyInstanceErr != nil {
		return nil, f.getCeremonyInstanceErr
	}
	return f.getCeremonyInstanceResp, nil
}

func (f *fakeQueryServer) GetBacklogReview(_ context.Context, _ *proxyv1.GetBacklogReviewRequest) (*proxyv1.GetBacklogReviewResponse, error) {
	if f.getBacklogReviewErr != nil {
		return nil, f.getBacklogReviewErr
	}
	return f.getBacklogReviewResp, nil
}

func (f *fakeQueryServer) ListBacklogReviews(_ context.Context, _ *proxyv1.ListBacklogReviewsRequest) (*proxyv1.ListBacklogReviewsResponse, error) {
	if f.listBacklogReviewsErr != nil {
		return nil, f.listBacklogReviewsErr
	}
	return f.listBacklogReviewsResp, nil
}

// ---------------------------------------------------------------------------
// fakeEnrollmentServer
// ---------------------------------------------------------------------------

type fakeEnrollmentServer struct {
	proxyv1.UnimplementedEnrollmentServiceServer

	enrollResp *proxyv1.EnrollResponse
	enrollErr  error

	renewResp *proxyv1.RenewResponse
	renewErr  error
}

func (f *fakeEnrollmentServer) Enroll(_ context.Context, _ *proxyv1.EnrollRequest) (*proxyv1.EnrollResponse, error) {
	if f.enrollErr != nil {
		return nil, f.enrollErr
	}
	return f.enrollResp, nil
}

func (f *fakeEnrollmentServer) Renew(_ context.Context, _ *proxyv1.RenewRequest) (*proxyv1.RenewResponse, error) {
	if f.renewErr != nil {
		return nil, f.renewErr
	}
	return f.renewResp, nil
}

// ---------------------------------------------------------------------------
// Test server helper
// ---------------------------------------------------------------------------

func startTestServer(t *testing.T, cmd *fakeCommandServer, qry *fakeQueryServer) *FleetClient {
	t.Helper()
	return startTestServerFull(t, cmd, qry, &fakeEnrollmentServer{})
}

func startTestServerFull(t *testing.T, cmd *fakeCommandServer, qry *fakeQueryServer, enr *fakeEnrollmentServer) *FleetClient {
	t.Helper()
	lis := bufconn.Listen(testBufSize)
	srv := grpc.NewServer()

	proxyv1.RegisterFleetCommandServiceServer(srv, cmd)
	proxyv1.RegisterFleetQueryServiceServer(srv, qry)
	proxyv1.RegisterEnrollmentServiceServer(srv, enr)

	go func() { _ = srv.Serve(lis) }()
	t.Cleanup(srv.Stop)

	cc, err := grpc.NewClient(
		"passthrough:///bufnet",
		grpc.WithContextDialer(func(_ context.Context, _ string) (net.Conn, error) {
			return lis.Dial()
		}),
		grpc.WithTransportCredentials(insecure.NewCredentials()),
	)
	if err != nil {
		t.Fatalf("dial bufconn: %v", err)
	}
	t.Cleanup(func() { cc.Close() })

	return NewFleetClient(&Connection{conn: cc, target: "bufnet"})
}

// ---------------------------------------------------------------------------
// Reusable backlog review proto fixture
// ---------------------------------------------------------------------------

func testBacklogReviewProto() *proxyv1.BacklogReview {
	return &proxyv1.BacklogReview{
		CeremonyId: "cer-br-1",
		Status:     "IN_PROGRESS",
		StoryIds:   []string{"s-1", "s-2"},
		CreatedBy:  "po-alice",
		CreatedAt:  "2025-06-01T00:00:00Z",
		UpdatedAt:  "2025-06-02T00:00:00Z",
		StartedAt:  "2025-06-01T01:00:00Z",
		ReviewResults: []*proxyv1.StoryReviewResult{
			{
				StoryId:           "s-1",
				ArchitectFeedback: "looks good",
				QaFeedback:        "tests needed",
				DevopsFeedback:    "CI ready",
				ApprovalStatus:    "APPROVED",
				ReviewedAt:        "2025-06-01T02:00:00Z",
				ApprovedBy:        "po-alice",
				ApprovedAt:        "2025-06-01T03:00:00Z",
				PoNotes:           "ship it",
				Recommendations:   []string{"add metrics"},
				PlanId:            "plan-1",
				PlanPreliminary: &proxyv1.PlanPreliminary{
					Title:               "Story 1 Plan",
					Description:         "Implement feature X",
					TechnicalNotes:      "Use adapter pattern",
					EstimatedComplexity: "medium",
					AcceptanceCriteria:  []string{"AC1", "AC2"},
					Roles:               []string{"dev", "qa"},
					Dependencies:        []string{"dep-A"},
					TasksOutline:        []string{"task-1", "task-2"},
				},
			},
		},
	}
}

// ===========================================================================
// Tests: CreateProject
// ===========================================================================

func TestFleetClient_CreateProject(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name       string
		resp       *proxyv1.CreateProjectResponse
		serverErr  error
		wantErr    bool
		wantSubstr string
		wantID     string
	}{
		{
			name:   "success",
			resp:   &proxyv1.CreateProjectResponse{ProjectId: "proj-123", Success: true},
			wantID: "proj-123",
		},
		{
			name:       "server error",
			serverErr:  status.Error(codes.Internal, "db failure"),
			wantErr:    true,
			wantSubstr: "create_project RPC",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			client := startTestServer(t,
				&fakeCommandServer{createProjectResp: tt.resp, createProjectErr: tt.serverErr},
				&fakeQueryServer{},
			)

			got, err := client.CreateProject(context.Background(), "req-1", "My Project", "A test project")
			if tt.wantErr {
				if err == nil {
					t.Fatal("expected error, got nil")
				}
				if tt.wantSubstr != "" && !strings.Contains(err.Error(), tt.wantSubstr) {
					t.Errorf("error %q does not contain %q", err, tt.wantSubstr)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if got.ID != tt.wantID {
				t.Errorf("ID = %q, want %q", got.ID, tt.wantID)
			}
			if got.Name != "My Project" {
				t.Errorf("Name = %q, want %q", got.Name, "My Project")
			}
			if got.Description != "A test project" {
				t.Errorf("Description = %q, want %q", got.Description, "A test project")
			}
		})
	}
}

// ===========================================================================
// Tests: ListProjects
// ===========================================================================

func TestFleetClient_ListProjects(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name       string
		resp       *proxyv1.ListProjectsResponse
		serverErr  error
		wantErr    bool
		wantSubstr string
		wantLen    int
	}{
		{
			name:    "empty list",
			resp:    &proxyv1.ListProjectsResponse{},
			wantLen: 0,
		},
		{
			name: "multiple projects with full field mapping",
			resp: &proxyv1.ListProjectsResponse{
				Projects: []*proxyv1.Project{
					{
						ProjectId:   "p1",
						Name:        "Alpha",
						Description: "First project",
						Status:      "active",
						Owner:       "alice",
						CreatedAt:   "2025-01-01T00:00:00Z",
						UpdatedAt:   "2025-01-02T00:00:00Z",
					},
					{
						ProjectId:   "p2",
						Name:        "Beta",
						Description: "Second project",
						Status:      "draft",
						Owner:       "bob",
						CreatedAt:   "2025-02-01T00:00:00Z",
						UpdatedAt:   "2025-02-02T00:00:00Z",
					},
				},
				TotalCount: 2,
			},
			wantLen: 2,
		},
		{
			name:       "server error",
			serverErr:  status.Error(codes.Unavailable, "service down"),
			wantErr:    true,
			wantSubstr: "list_projects RPC",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			client := startTestServer(t,
				&fakeCommandServer{},
				&fakeQueryServer{listProjectsResp: tt.resp, listProjectsErr: tt.serverErr},
			)

			got, _, err := client.ListProjects(context.Background(), "", 100, 0)
			if tt.wantErr {
				if err == nil {
					t.Fatal("expected error, got nil")
				}
				if tt.wantSubstr != "" && !strings.Contains(err.Error(), tt.wantSubstr) {
					t.Errorf("error %q does not contain %q", err, tt.wantSubstr)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if len(got) != tt.wantLen {
				t.Fatalf("len = %d, want %d", len(got), tt.wantLen)
			}
			if tt.wantLen < 2 {
				return
			}
			p := got[0]
			if p.ID != "p1" {
				t.Errorf("projects[0].ID = %q, want %q", p.ID, "p1")
			}
			if p.Name != "Alpha" {
				t.Errorf("projects[0].Name = %q, want %q", p.Name, "Alpha")
			}
			if p.Description != "First project" {
				t.Errorf("projects[0].Description = %q, want %q", p.Description, "First project")
			}
			if p.Status != "active" {
				t.Errorf("projects[0].Status = %q, want %q", p.Status, "active")
			}
			if p.Owner != "alice" {
				t.Errorf("projects[0].Owner = %q, want %q", p.Owner, "alice")
			}
			if p.CreatedAt != "2025-01-01T00:00:00Z" {
				t.Errorf("projects[0].CreatedAt = %q, want %q", p.CreatedAt, "2025-01-01T00:00:00Z")
			}
			if p.UpdatedAt != "2025-01-02T00:00:00Z" {
				t.Errorf("projects[0].UpdatedAt = %q, want %q", p.UpdatedAt, "2025-01-02T00:00:00Z")
			}
		})
	}
}

// ===========================================================================
// Tests: CreateEpic
// ===========================================================================

func TestFleetClient_CreateEpic(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name       string
		resp       *proxyv1.CreateEpicResponse
		serverErr  error
		wantErr    bool
		wantSubstr string
		wantID     string
	}{
		{
			name:   "success",
			resp:   &proxyv1.CreateEpicResponse{EpicId: "epic-42", Success: true},
			wantID: "epic-42",
		},
		{
			name:       "server error",
			serverErr:  status.Error(codes.Internal, "storage failure"),
			wantErr:    true,
			wantSubstr: "create_epic RPC",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			client := startTestServer(t,
				&fakeCommandServer{createEpicResp: tt.resp, createEpicErr: tt.serverErr},
				&fakeQueryServer{},
			)

			got, err := client.CreateEpic(context.Background(), "req-1", "proj-1", "My Epic", "An epic description")
			if tt.wantErr {
				if err == nil {
					t.Fatal("expected error, got nil")
				}
				if tt.wantSubstr != "" && !strings.Contains(err.Error(), tt.wantSubstr) {
					t.Errorf("error %q does not contain %q", err, tt.wantSubstr)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if got.ID != tt.wantID {
				t.Errorf("ID = %q, want %q", got.ID, tt.wantID)
			}
			if got.ProjectID != "proj-1" {
				t.Errorf("ProjectID = %q, want %q", got.ProjectID, "proj-1")
			}
			if got.Title != "My Epic" {
				t.Errorf("Title = %q, want %q", got.Title, "My Epic")
			}
			if got.Description != "An epic description" {
				t.Errorf("Description = %q, want %q", got.Description, "An epic description")
			}
		})
	}
}

// ===========================================================================
// Tests: CreateStory
// ===========================================================================

func TestFleetClient_CreateStory(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name       string
		resp       *proxyv1.CreateStoryResponse
		serverErr  error
		wantErr    bool
		wantSubstr string
		wantID     string
	}{
		{
			name:   "success",
			resp:   &proxyv1.CreateStoryResponse{StoryId: "story-99", Success: true},
			wantID: "story-99",
		},
		{
			name:       "server error",
			serverErr:  status.Error(codes.PermissionDenied, "forbidden"),
			wantErr:    true,
			wantSubstr: "create_story RPC",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			client := startTestServer(t,
				&fakeCommandServer{createStoryResp: tt.resp, createStoryErr: tt.serverErr},
				&fakeQueryServer{},
			)

			got, err := client.CreateStory(context.Background(), "req-1", "epic-1", "Story Title", "Story brief")
			if tt.wantErr {
				if err == nil {
					t.Fatal("expected error, got nil")
				}
				if tt.wantSubstr != "" && !strings.Contains(err.Error(), tt.wantSubstr) {
					t.Errorf("error %q does not contain %q", err, tt.wantSubstr)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if got.ID != tt.wantID {
				t.Errorf("ID = %q, want %q", got.ID, tt.wantID)
			}
			if got.EpicID != "epic-1" {
				t.Errorf("EpicID = %q, want %q", got.EpicID, "epic-1")
			}
			if got.Title != "Story Title" {
				t.Errorf("Title = %q, want %q", got.Title, "Story Title")
			}
			if got.Brief != "Story brief" {
				t.Errorf("Brief = %q, want %q", got.Brief, "Story brief")
			}
		})
	}
}

// ===========================================================================
// Tests: TransitionStory
// ===========================================================================

func TestFleetClient_TransitionStory(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name       string
		resp       *proxyv1.TransitionStoryResponse
		serverErr  error
		wantErr    bool
		wantSubstr string
	}{
		{
			name: "success",
			resp: &proxyv1.TransitionStoryResponse{Success: true},
		},
		{
			name:       "server error",
			serverErr:  status.Error(codes.NotFound, "story not found"),
			wantErr:    true,
			wantSubstr: "transition_story RPC",
		},
		{
			name:       "transition failed (success=false)",
			resp:       &proxyv1.TransitionStoryResponse{Success: false, Message: "invalid transition"},
			wantErr:    true,
			wantSubstr: "transition failed",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			client := startTestServer(t,
				&fakeCommandServer{transitionStoryResp: tt.resp, transitionStoryErr: tt.serverErr},
				&fakeQueryServer{},
			)

			err := client.TransitionStory(context.Background(), "story-1", "IN_PROGRESS")
			if tt.wantErr {
				if err == nil {
					t.Fatal("expected error, got nil")
				}
				if tt.wantSubstr != "" && !strings.Contains(err.Error(), tt.wantSubstr) {
					t.Errorf("error %q does not contain %q", err, tt.wantSubstr)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
		})
	}
}

// ===========================================================================
// Tests: StartCeremony
// ===========================================================================

func TestFleetClient_StartCeremony(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name           string
		resp           *proxyv1.StartPlanningCeremonyResponse
		serverErr      error
		wantErr        bool
		wantSubstr     string
		wantInstanceID string
		wantStatus     string
	}{
		{
			name:           "success",
			resp:           &proxyv1.StartPlanningCeremonyResponse{InstanceId: "inst-1", Status: "RUNNING"},
			wantInstanceID: "inst-1",
			wantStatus:     "RUNNING",
		},
		{
			name:       "server error",
			serverErr:  status.Error(codes.Internal, "orchestrator down"),
			wantErr:    true,
			wantSubstr: "start_ceremony RPC",
		},
		{
			name:       "ceremony failed status",
			resp:       &proxyv1.StartPlanningCeremonyResponse{Status: "FAILED", Message: "step validation failed"},
			wantErr:    true,
			wantSubstr: "start ceremony failed",
		},
		{
			name:       "ceremony error status",
			resp:       &proxyv1.StartPlanningCeremonyResponse{Status: "ERROR", Message: "internal error"},
			wantErr:    true,
			wantSubstr: "start ceremony failed",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			client := startTestServer(t,
				&fakeCommandServer{startCeremonyResp: tt.resp, startCeremonyErr: tt.serverErr},
				&fakeQueryServer{},
			)

			got, err := client.StartCeremony(context.Background(), "req-1", "cer-1", "planning", "story-1", []string{"step-a", "step-b"})
			if tt.wantErr {
				if err == nil {
					t.Fatal("expected error, got nil")
				}
				if tt.wantSubstr != "" && !strings.Contains(err.Error(), tt.wantSubstr) {
					t.Errorf("error %q does not contain %q", err, tt.wantSubstr)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if got.InstanceID != tt.wantInstanceID {
				t.Errorf("InstanceID = %q, want %q", got.InstanceID, tt.wantInstanceID)
			}
			if got.Status != tt.wantStatus {
				t.Errorf("Status = %q, want %q", got.Status, tt.wantStatus)
			}
		})
	}
}

// ===========================================================================
// Tests: ListEpics
// ===========================================================================

func TestFleetClient_ListEpics(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name       string
		resp       *proxyv1.ListEpicsResponse
		serverErr  error
		wantErr    bool
		wantSubstr string
		wantLen    int
	}{
		{
			name:    "empty list",
			resp:    &proxyv1.ListEpicsResponse{},
			wantLen: 0,
		},
		{
			name: "multiple epics with full field mapping",
			resp: &proxyv1.ListEpicsResponse{
				Epics: []*proxyv1.Epic{
					{
						EpicId:      "e-1",
						ProjectId:   "proj-1",
						Title:       "Auth Epic",
						Description: "Authentication features",
						Status:      "active",
						CreatedAt:   "2025-03-01T00:00:00Z",
						UpdatedAt:   "2025-03-02T00:00:00Z",
					},
					{
						EpicId:      "e-2",
						ProjectId:   "proj-1",
						Title:       "Billing Epic",
						Description: "Billing features",
						Status:      "draft",
						CreatedAt:   "2025-04-01T00:00:00Z",
						UpdatedAt:   "2025-04-02T00:00:00Z",
					},
				},
				TotalCount: 2,
			},
			wantLen: 2,
		},
		{
			name:       "server error",
			serverErr:  status.Error(codes.Unavailable, "service down"),
			wantErr:    true,
			wantSubstr: "list_epics RPC",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			client := startTestServer(t,
				&fakeCommandServer{},
				&fakeQueryServer{listEpicsResp: tt.resp, listEpicsErr: tt.serverErr},
			)

			got, total, err := client.ListEpics(context.Background(), "proj-1", "", 100, 0)
			if tt.wantErr {
				if err == nil {
					t.Fatal("expected error, got nil")
				}
				if tt.wantSubstr != "" && !strings.Contains(err.Error(), tt.wantSubstr) {
					t.Errorf("error %q does not contain %q", err, tt.wantSubstr)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if len(got) != tt.wantLen {
				t.Fatalf("len = %d, want %d", len(got), tt.wantLen)
			}
			if tt.wantLen < 2 {
				return
			}
			if total != 2 {
				t.Errorf("totalCount = %d, want 2", total)
			}
			e := got[0]
			if e.ID != "e-1" {
				t.Errorf("epics[0].ID = %q, want %q", e.ID, "e-1")
			}
			if e.ProjectID != "proj-1" {
				t.Errorf("epics[0].ProjectID = %q, want %q", e.ProjectID, "proj-1")
			}
			if e.Title != "Auth Epic" {
				t.Errorf("epics[0].Title = %q, want %q", e.Title, "Auth Epic")
			}
			if e.Description != "Authentication features" {
				t.Errorf("epics[0].Description = %q, want %q", e.Description, "Authentication features")
			}
			if e.Status != "active" {
				t.Errorf("epics[0].Status = %q, want %q", e.Status, "active")
			}
			if e.CreatedAt != "2025-03-01T00:00:00Z" {
				t.Errorf("epics[0].CreatedAt = %q, want %q", e.CreatedAt, "2025-03-01T00:00:00Z")
			}
			if e.UpdatedAt != "2025-03-02T00:00:00Z" {
				t.Errorf("epics[0].UpdatedAt = %q, want %q", e.UpdatedAt, "2025-03-02T00:00:00Z")
			}
		})
	}
}

// ===========================================================================
// Tests: ListStories
// ===========================================================================

func TestFleetClient_ListStories(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name       string
		resp       *proxyv1.ListStoriesResponse
		serverErr  error
		wantErr    bool
		wantSubstr string
		wantLen    int
	}{
		{
			name:    "empty list",
			resp:    &proxyv1.ListStoriesResponse{},
			wantLen: 0,
		},
		{
			name: "stories with full field mapping",
			resp: &proxyv1.ListStoriesResponse{
				Stories: []*proxyv1.Story{
					{
						StoryId:   "s-1",
						EpicId:    "e-1",
						Title:     "Login flow",
						Brief:     "Implement login",
						State:     "IN_PROGRESS",
						DorScore:  85,
						CreatedBy: "alice",
						CreatedAt: "2025-05-01T00:00:00Z",
						UpdatedAt: "2025-05-02T00:00:00Z",
					},
				},
				TotalCount: 1,
			},
			wantLen: 1,
		},
		{
			name:       "server error",
			serverErr:  status.Error(codes.Internal, "query failed"),
			wantErr:    true,
			wantSubstr: "list_stories RPC",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			client := startTestServer(t,
				&fakeCommandServer{},
				&fakeQueryServer{listStoriesResp: tt.resp, listStoriesErr: tt.serverErr},
			)

			got, total, err := client.ListStories(context.Background(), "e-1", "", 100, 0)
			if tt.wantErr {
				if err == nil {
					t.Fatal("expected error, got nil")
				}
				if tt.wantSubstr != "" && !strings.Contains(err.Error(), tt.wantSubstr) {
					t.Errorf("error %q does not contain %q", err, tt.wantSubstr)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if len(got) != tt.wantLen {
				t.Fatalf("len = %d, want %d", len(got), tt.wantLen)
			}
			if tt.wantLen == 0 {
				return
			}
			if total != 1 {
				t.Errorf("totalCount = %d, want 1", total)
			}
			s := got[0]
			if s.ID != "s-1" {
				t.Errorf("stories[0].ID = %q, want %q", s.ID, "s-1")
			}
			if s.EpicID != "e-1" {
				t.Errorf("stories[0].EpicID = %q, want %q", s.EpicID, "e-1")
			}
			if s.Title != "Login flow" {
				t.Errorf("stories[0].Title = %q, want %q", s.Title, "Login flow")
			}
			if s.Brief != "Implement login" {
				t.Errorf("stories[0].Brief = %q, want %q", s.Brief, "Implement login")
			}
			if s.State != "IN_PROGRESS" {
				t.Errorf("stories[0].State = %q, want %q", s.State, "IN_PROGRESS")
			}
			if s.DorScore != 85 {
				t.Errorf("stories[0].DorScore = %d, want %d", s.DorScore, 85)
			}
			if s.CreatedBy != "alice" {
				t.Errorf("stories[0].CreatedBy = %q, want %q", s.CreatedBy, "alice")
			}
			if s.CreatedAt != "2025-05-01T00:00:00Z" {
				t.Errorf("stories[0].CreatedAt = %q, want %q", s.CreatedAt, "2025-05-01T00:00:00Z")
			}
			if s.UpdatedAt != "2025-05-02T00:00:00Z" {
				t.Errorf("stories[0].UpdatedAt = %q, want %q", s.UpdatedAt, "2025-05-02T00:00:00Z")
			}
		})
	}
}

// ===========================================================================
// Tests: CreateTask
// ===========================================================================

func TestFleetClient_CreateTask(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name       string
		resp       *proxyv1.CreateTaskResponse
		serverErr  error
		wantErr    bool
		wantSubstr string
		wantID     string
	}{
		{
			name:   "success",
			resp:   &proxyv1.CreateTaskResponse{TaskId: "task-7", Success: true},
			wantID: "task-7",
		},
		{
			name:       "server error",
			serverErr:  status.Error(codes.InvalidArgument, "missing title"),
			wantErr:    true,
			wantSubstr: "create_task RPC",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			client := startTestServer(t,
				&fakeCommandServer{createTaskResp: tt.resp, createTaskErr: tt.serverErr},
				&fakeQueryServer{},
			)

			got, err := client.CreateTask(context.Background(), "req-1", "story-1", "Write tests", "Write unit tests", "dev", "bob", 4, 1)
			if tt.wantErr {
				if err == nil {
					t.Fatal("expected error, got nil")
				}
				if tt.wantSubstr != "" && !strings.Contains(err.Error(), tt.wantSubstr) {
					t.Errorf("error %q does not contain %q", err, tt.wantSubstr)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if got.ID != tt.wantID {
				t.Errorf("ID = %q, want %q", got.ID, tt.wantID)
			}
			if got.StoryID != "story-1" {
				t.Errorf("StoryID = %q, want %q", got.StoryID, "story-1")
			}
			if got.Title != "Write tests" {
				t.Errorf("Title = %q, want %q", got.Title, "Write tests")
			}
			if got.Description != "Write unit tests" {
				t.Errorf("Description = %q, want %q", got.Description, "Write unit tests")
			}
			if got.Type != "dev" {
				t.Errorf("Type = %q, want %q", got.Type, "dev")
			}
			if got.AssignedTo != "bob" {
				t.Errorf("AssignedTo = %q, want %q", got.AssignedTo, "bob")
			}
			if got.EstimatedHours != 4 {
				t.Errorf("EstimatedHours = %d, want %d", got.EstimatedHours, 4)
			}
			if got.Priority != 1 {
				t.Errorf("Priority = %d, want %d", got.Priority, 1)
			}
		})
	}
}

// ===========================================================================
// Tests: ListTasks
// ===========================================================================

func TestFleetClient_ListTasks(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name       string
		resp       *proxyv1.ListTasksResponse
		serverErr  error
		wantErr    bool
		wantSubstr string
		wantLen    int
	}{
		{
			name:    "empty list",
			resp:    &proxyv1.ListTasksResponse{},
			wantLen: 0,
		},
		{
			name: "tasks with full field mapping",
			resp: &proxyv1.ListTasksResponse{
				Tasks: []*proxyv1.Task{
					{
						TaskId:         "t-1",
						StoryId:        "s-1",
						Title:          "Implement handler",
						Description:    "Add HTTP handler",
						Type:           "dev",
						Status:         "TODO",
						AssignedTo:     "carol",
						EstimatedHours: 8,
						Priority:       2,
						CreatedAt:      "2025-05-10T00:00:00Z",
						UpdatedAt:      "2025-05-11T00:00:00Z",
					},
				},
				TotalCount: 1,
			},
			wantLen: 1,
		},
		{
			name:       "server error",
			serverErr:  status.Error(codes.Internal, "db timeout"),
			wantErr:    true,
			wantSubstr: "list_tasks RPC",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			client := startTestServer(t,
				&fakeCommandServer{},
				&fakeQueryServer{listTasksResp: tt.resp, listTasksErr: tt.serverErr},
			)

			got, total, err := client.ListTasks(context.Background(), "s-1", "", 100, 0)
			if tt.wantErr {
				if err == nil {
					t.Fatal("expected error, got nil")
				}
				if tt.wantSubstr != "" && !strings.Contains(err.Error(), tt.wantSubstr) {
					t.Errorf("error %q does not contain %q", err, tt.wantSubstr)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if len(got) != tt.wantLen {
				t.Fatalf("len = %d, want %d", len(got), tt.wantLen)
			}
			if tt.wantLen == 0 {
				return
			}
			if total != 1 {
				t.Errorf("totalCount = %d, want 1", total)
			}
			tk := got[0]
			if tk.ID != "t-1" {
				t.Errorf("tasks[0].ID = %q, want %q", tk.ID, "t-1")
			}
			if tk.StoryID != "s-1" {
				t.Errorf("tasks[0].StoryID = %q, want %q", tk.StoryID, "s-1")
			}
			if tk.Title != "Implement handler" {
				t.Errorf("tasks[0].Title = %q, want %q", tk.Title, "Implement handler")
			}
			if tk.Description != "Add HTTP handler" {
				t.Errorf("tasks[0].Description = %q, want %q", tk.Description, "Add HTTP handler")
			}
			if tk.Type != "dev" {
				t.Errorf("tasks[0].Type = %q, want %q", tk.Type, "dev")
			}
			if tk.Status != "TODO" {
				t.Errorf("tasks[0].Status = %q, want %q", tk.Status, "TODO")
			}
			if tk.AssignedTo != "carol" {
				t.Errorf("tasks[0].AssignedTo = %q, want %q", tk.AssignedTo, "carol")
			}
			if tk.EstimatedHours != 8 {
				t.Errorf("tasks[0].EstimatedHours = %d, want %d", tk.EstimatedHours, 8)
			}
			if tk.Priority != 2 {
				t.Errorf("tasks[0].Priority = %d, want %d", tk.Priority, 2)
			}
			if tk.CreatedAt != "2025-05-10T00:00:00Z" {
				t.Errorf("tasks[0].CreatedAt = %q, want %q", tk.CreatedAt, "2025-05-10T00:00:00Z")
			}
			if tk.UpdatedAt != "2025-05-11T00:00:00Z" {
				t.Errorf("tasks[0].UpdatedAt = %q, want %q", tk.UpdatedAt, "2025-05-11T00:00:00Z")
			}
		})
	}
}

// ===========================================================================
// Tests: ListCeremonies
// ===========================================================================

func TestFleetClient_ListCeremonies(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name       string
		resp       *proxyv1.ListCeremonyInstancesResponse
		serverErr  error
		wantErr    bool
		wantSubstr string
		wantLen    int
	}{
		{
			name:    "empty list",
			resp:    &proxyv1.ListCeremonyInstancesResponse{},
			wantLen: 0,
		},
		{
			name: "ceremonies with full field mapping",
			resp: &proxyv1.ListCeremonyInstancesResponse{
				Ceremonies: []*proxyv1.CeremonyInstance{
					{
						InstanceId:     "inst-1",
						CeremonyId:     "cer-1",
						StoryId:        "story-1",
						DefinitionName: "planning",
						CurrentState:   "STEP_2",
						Status:         "RUNNING",
						CorrelationId:  "corr-abc",
						StepStatus:     map[string]string{"step-a": "DONE", "step-b": "RUNNING"},
						StepOutputs:    map[string]string{"step-a": "output-a"},
						CreatedAt:      "2025-05-01T00:00:00Z",
						UpdatedAt:      "2025-05-02T00:00:00Z",
					},
				},
				TotalCount: 1,
			},
			wantLen: 1,
		},
		{
			name:       "server error",
			serverErr:  status.Error(codes.Unavailable, "service down"),
			wantErr:    true,
			wantSubstr: "list_ceremony_instances RPC",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			client := startTestServer(t,
				&fakeCommandServer{},
				&fakeQueryServer{listCeremonyInstancesResp: tt.resp, listCeremonyInstancesErr: tt.serverErr},
			)

			got, total, err := client.ListCeremonies(context.Background(), "story-1", "", 100, 0)
			if tt.wantErr {
				if err == nil {
					t.Fatal("expected error, got nil")
				}
				if tt.wantSubstr != "" && !strings.Contains(err.Error(), tt.wantSubstr) {
					t.Errorf("error %q does not contain %q", err, tt.wantSubstr)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if len(got) != tt.wantLen {
				t.Fatalf("len = %d, want %d", len(got), tt.wantLen)
			}
			if tt.wantLen == 0 {
				return
			}
			if total != 1 {
				t.Errorf("totalCount = %d, want 1", total)
			}
			c := got[0]
			if c.InstanceID != "inst-1" {
				t.Errorf("ceremonies[0].InstanceID = %q, want %q", c.InstanceID, "inst-1")
			}
			if c.CeremonyID != "cer-1" {
				t.Errorf("ceremonies[0].CeremonyID = %q, want %q", c.CeremonyID, "cer-1")
			}
			if c.StoryID != "story-1" {
				t.Errorf("ceremonies[0].StoryID = %q, want %q", c.StoryID, "story-1")
			}
			if c.DefinitionName != "planning" {
				t.Errorf("ceremonies[0].DefinitionName = %q, want %q", c.DefinitionName, "planning")
			}
			if c.CurrentState != "STEP_2" {
				t.Errorf("ceremonies[0].CurrentState = %q, want %q", c.CurrentState, "STEP_2")
			}
			if c.Status != "RUNNING" {
				t.Errorf("ceremonies[0].Status = %q, want %q", c.Status, "RUNNING")
			}
			if c.CorrelationID != "corr-abc" {
				t.Errorf("ceremonies[0].CorrelationID = %q, want %q", c.CorrelationID, "corr-abc")
			}
			if c.StepStatuses["step-a"] != "DONE" {
				t.Errorf("ceremonies[0].StepStatuses[step-a] = %q, want %q", c.StepStatuses["step-a"], "DONE")
			}
			if c.StepOutputs["step-a"] != "output-a" {
				t.Errorf("ceremonies[0].StepOutputs[step-a] = %q, want %q", c.StepOutputs["step-a"], "output-a")
			}
			if c.CreatedAt != "2025-05-01T00:00:00Z" {
				t.Errorf("ceremonies[0].CreatedAt = %q, want %q", c.CreatedAt, "2025-05-01T00:00:00Z")
			}
			if c.UpdatedAt != "2025-05-02T00:00:00Z" {
				t.Errorf("ceremonies[0].UpdatedAt = %q, want %q", c.UpdatedAt, "2025-05-02T00:00:00Z")
			}
		})
	}
}

// ===========================================================================
// Tests: GetCeremony
// ===========================================================================

func TestFleetClient_GetCeremony(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name           string
		resp           *proxyv1.CeremonyInstanceResponse
		serverErr      error
		wantErr        bool
		wantSubstr     string
		wantInstanceID string
	}{
		{
			name: "success",
			resp: &proxyv1.CeremonyInstanceResponse{
				Ceremony: &proxyv1.CeremonyInstance{
					InstanceId:     "inst-5",
					CeremonyId:     "cer-5",
					StoryId:        "story-5",
					DefinitionName: "backlog_review",
					CurrentState:   "DELIBERATION",
					Status:         "RUNNING",
					CorrelationId:  "corr-xyz",
					StepStatus:     map[string]string{"init": "DONE"},
					StepOutputs:    map[string]string{"init": "initialized"},
					CreatedAt:      "2025-06-01T00:00:00Z",
					UpdatedAt:      "2025-06-02T00:00:00Z",
				},
			},
			wantInstanceID: "inst-5",
		},
		{
			name:       "server error",
			serverErr:  status.Error(codes.NotFound, "instance not found"),
			wantErr:    true,
			wantSubstr: "get_ceremony_instance RPC",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			client := startTestServer(t,
				&fakeCommandServer{},
				&fakeQueryServer{getCeremonyInstanceResp: tt.resp, getCeremonyInstanceErr: tt.serverErr},
			)

			got, err := client.GetCeremony(context.Background(), "inst-5")
			if tt.wantErr {
				if err == nil {
					t.Fatal("expected error, got nil")
				}
				if tt.wantSubstr != "" && !strings.Contains(err.Error(), tt.wantSubstr) {
					t.Errorf("error %q does not contain %q", err, tt.wantSubstr)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if got.InstanceID != tt.wantInstanceID {
				t.Errorf("InstanceID = %q, want %q", got.InstanceID, tt.wantInstanceID)
			}
			if got.CeremonyID != "cer-5" {
				t.Errorf("CeremonyID = %q, want %q", got.CeremonyID, "cer-5")
			}
			if got.StoryID != "story-5" {
				t.Errorf("StoryID = %q, want %q", got.StoryID, "story-5")
			}
			if got.DefinitionName != "backlog_review" {
				t.Errorf("DefinitionName = %q, want %q", got.DefinitionName, "backlog_review")
			}
			if got.CurrentState != "DELIBERATION" {
				t.Errorf("CurrentState = %q, want %q", got.CurrentState, "DELIBERATION")
			}
			if got.Status != "RUNNING" {
				t.Errorf("Status = %q, want %q", got.Status, "RUNNING")
			}
			if got.CorrelationID != "corr-xyz" {
				t.Errorf("CorrelationID = %q, want %q", got.CorrelationID, "corr-xyz")
			}
			if got.StepStatuses["init"] != "DONE" {
				t.Errorf("StepStatuses[init] = %q, want %q", got.StepStatuses["init"], "DONE")
			}
			if got.StepOutputs["init"] != "initialized" {
				t.Errorf("StepOutputs[init] = %q, want %q", got.StepOutputs["init"], "initialized")
			}
		})
	}
}

// ===========================================================================
// Tests: ApproveDecision
// ===========================================================================

func TestFleetClient_ApproveDecision(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name       string
		resp       *proxyv1.ApproveDecisionResponse
		serverErr  error
		wantErr    bool
		wantSubstr string
	}{
		{
			name: "success",
			resp: &proxyv1.ApproveDecisionResponse{Success: true},
		},
		{
			name:       "server error",
			serverErr:  status.Error(codes.NotFound, "decision not found"),
			wantErr:    true,
			wantSubstr: "approve_decision RPC",
		},
		{
			name:       "approve failed (success=false)",
			resp:       &proxyv1.ApproveDecisionResponse{Success: false, Message: "decision already resolved"},
			wantErr:    true,
			wantSubstr: "approve decision failed",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			client := startTestServer(t,
				&fakeCommandServer{approveDecisionResp: tt.resp, approveDecisionErr: tt.serverErr},
				&fakeQueryServer{},
			)

			err := client.ApproveDecision(context.Background(), "story-1", "dec-1", "LGTM")
			if tt.wantErr {
				if err == nil {
					t.Fatal("expected error, got nil")
				}
				if tt.wantSubstr != "" && !strings.Contains(err.Error(), tt.wantSubstr) {
					t.Errorf("error %q does not contain %q", err, tt.wantSubstr)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
		})
	}
}

// ===========================================================================
// Tests: RejectDecision
// ===========================================================================

func TestFleetClient_RejectDecision(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name       string
		resp       *proxyv1.RejectDecisionResponse
		serverErr  error
		wantErr    bool
		wantSubstr string
	}{
		{
			name: "success",
			resp: &proxyv1.RejectDecisionResponse{Success: true},
		},
		{
			name:       "server error",
			serverErr:  status.Error(codes.NotFound, "decision not found"),
			wantErr:    true,
			wantSubstr: "reject_decision RPC",
		},
		{
			name:       "reject failed (success=false)",
			resp:       &proxyv1.RejectDecisionResponse{Success: false, Message: "decision already resolved"},
			wantErr:    true,
			wantSubstr: "reject decision failed",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			client := startTestServer(t,
				&fakeCommandServer{rejectDecisionResp: tt.resp, rejectDecisionErr: tt.serverErr},
				&fakeQueryServer{},
			)

			err := client.RejectDecision(context.Background(), "story-1", "dec-1", "needs rework")
			if tt.wantErr {
				if err == nil {
					t.Fatal("expected error, got nil")
				}
				if tt.wantSubstr != "" && !strings.Contains(err.Error(), tt.wantSubstr) {
					t.Errorf("error %q does not contain %q", err, tt.wantSubstr)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
		})
	}
}

// ===========================================================================
// Tests: CreateBacklogReview
// ===========================================================================

func TestFleetClient_CreateBacklogReview(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name           string
		resp           *proxyv1.CreateBacklogReviewResponse
		serverErr      error
		wantErr        bool
		wantSubstr     string
		wantCeremonyID string
	}{
		{
			name: "success",
			resp: &proxyv1.CreateBacklogReviewResponse{
				Ceremony: testBacklogReviewProto(),
				Success:  true,
			},
			wantCeremonyID: "cer-br-1",
		},
		{
			name:       "server error",
			serverErr:  status.Error(codes.Internal, "db failure"),
			wantErr:    true,
			wantSubstr: "create_backlog_review RPC",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			client := startTestServer(t,
				&fakeCommandServer{createBacklogReviewResp: tt.resp, createBacklogReviewErr: tt.serverErr},
				&fakeQueryServer{},
			)

			got, err := client.CreateBacklogReview(context.Background(), "req-1", []string{"s-1", "s-2"})
			if tt.wantErr {
				if err == nil {
					t.Fatal("expected error, got nil")
				}
				if tt.wantSubstr != "" && !strings.Contains(err.Error(), tt.wantSubstr) {
					t.Errorf("error %q does not contain %q", err, tt.wantSubstr)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if got.CeremonyID != tt.wantCeremonyID {
				t.Errorf("CeremonyID = %q, want %q", got.CeremonyID, tt.wantCeremonyID)
			}
			if got.Status != "IN_PROGRESS" {
				t.Errorf("Status = %q, want %q", got.Status, "IN_PROGRESS")
			}
			if got.CreatedBy != "po-alice" {
				t.Errorf("CreatedBy = %q, want %q", got.CreatedBy, "po-alice")
			}
			if len(got.StoryIDs) != 2 {
				t.Fatalf("StoryIDs len = %d, want 2", len(got.StoryIDs))
			}
			if got.StoryIDs[0] != "s-1" {
				t.Errorf("StoryIDs[0] = %q, want %q", got.StoryIDs[0], "s-1")
			}
			// Verify review result mapping
			if len(got.ReviewResults) != 1 {
				t.Fatalf("ReviewResults len = %d, want 1", len(got.ReviewResults))
			}
			rr := got.ReviewResults[0]
			if rr.StoryID != "s-1" {
				t.Errorf("ReviewResults[0].StoryID = %q, want %q", rr.StoryID, "s-1")
			}
			if rr.ArchitectFeedback != "looks good" {
				t.Errorf("ReviewResults[0].ArchitectFeedback = %q, want %q", rr.ArchitectFeedback, "looks good")
			}
			if rr.QAFeedback != "tests needed" {
				t.Errorf("ReviewResults[0].QAFeedback = %q, want %q", rr.QAFeedback, "tests needed")
			}
			if rr.DevopsFeedback != "CI ready" {
				t.Errorf("ReviewResults[0].DevopsFeedback = %q, want %q", rr.DevopsFeedback, "CI ready")
			}
			if rr.ApprovalStatus != "APPROVED" {
				t.Errorf("ReviewResults[0].ApprovalStatus = %q, want %q", rr.ApprovalStatus, "APPROVED")
			}
			if rr.PlanID != "plan-1" {
				t.Errorf("ReviewResults[0].PlanID = %q, want %q", rr.PlanID, "plan-1")
			}
			if rr.PONotes != "ship it" {
				t.Errorf("ReviewResults[0].PONotes = %q, want %q", rr.PONotes, "ship it")
			}
			if len(rr.Recommendations) != 1 || rr.Recommendations[0] != "add metrics" {
				t.Errorf("ReviewResults[0].Recommendations = %v, want [add metrics]", rr.Recommendations)
			}
			// Verify PlanPreliminary mapping
			pp := rr.PlanPreliminary
			if pp.Title != "Story 1 Plan" {
				t.Errorf("PlanPreliminary.Title = %q, want %q", pp.Title, "Story 1 Plan")
			}
			if pp.Description != "Implement feature X" {
				t.Errorf("PlanPreliminary.Description = %q, want %q", pp.Description, "Implement feature X")
			}
			if pp.TechnicalNotes != "Use adapter pattern" {
				t.Errorf("PlanPreliminary.TechnicalNotes = %q, want %q", pp.TechnicalNotes, "Use adapter pattern")
			}
			if pp.EstimatedComplexity != "medium" {
				t.Errorf("PlanPreliminary.EstimatedComplexity = %q, want %q", pp.EstimatedComplexity, "medium")
			}
			if len(pp.AcceptanceCriteria) != 2 || pp.AcceptanceCriteria[0] != "AC1" {
				t.Errorf("PlanPreliminary.AcceptanceCriteria = %v, want [AC1 AC2]", pp.AcceptanceCriteria)
			}
			if len(pp.Roles) != 2 || pp.Roles[0] != "dev" {
				t.Errorf("PlanPreliminary.Roles = %v, want [dev qa]", pp.Roles)
			}
			if len(pp.Dependencies) != 1 || pp.Dependencies[0] != "dep-A" {
				t.Errorf("PlanPreliminary.Dependencies = %v, want [dep-A]", pp.Dependencies)
			}
			if len(pp.TasksOutline) != 2 || pp.TasksOutline[0] != "task-1" {
				t.Errorf("PlanPreliminary.TasksOutline = %v, want [task-1 task-2]", pp.TasksOutline)
			}
		})
	}
}

// ===========================================================================
// Tests: StartBacklogReview
// ===========================================================================

func TestFleetClient_StartBacklogReview(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name                   string
		resp                   *proxyv1.StartBacklogReviewResponse
		serverErr              error
		wantErr                bool
		wantSubstr             string
		wantCeremonyID         string
		wantTotalDeliberations int32
	}{
		{
			name: "success",
			resp: &proxyv1.StartBacklogReviewResponse{
				Ceremony:                    testBacklogReviewProto(),
				Success:                     true,
				TotalDeliberationsSubmitted: 3,
			},
			wantCeremonyID:         "cer-br-1",
			wantTotalDeliberations: 3,
		},
		{
			name:       "server error",
			serverErr:  status.Error(codes.FailedPrecondition, "ceremony not in CREATED state"),
			wantErr:    true,
			wantSubstr: "start_backlog_review RPC",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			client := startTestServer(t,
				&fakeCommandServer{startBacklogReviewResp: tt.resp, startBacklogReviewErr: tt.serverErr},
				&fakeQueryServer{},
			)

			got, totalDelib, err := client.StartBacklogReview(context.Background(), "req-1", "cer-br-1")
			if tt.wantErr {
				if err == nil {
					t.Fatal("expected error, got nil")
				}
				if tt.wantSubstr != "" && !strings.Contains(err.Error(), tt.wantSubstr) {
					t.Errorf("error %q does not contain %q", err, tt.wantSubstr)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if got.CeremonyID != tt.wantCeremonyID {
				t.Errorf("CeremonyID = %q, want %q", got.CeremonyID, tt.wantCeremonyID)
			}
			if totalDelib != tt.wantTotalDeliberations {
				t.Errorf("totalDeliberations = %d, want %d", totalDelib, tt.wantTotalDeliberations)
			}
		})
	}
}

// ===========================================================================
// Tests: GetBacklogReview
// ===========================================================================

func TestFleetClient_GetBacklogReview(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name           string
		resp           *proxyv1.GetBacklogReviewResponse
		serverErr      error
		wantErr        bool
		wantSubstr     string
		wantCeremonyID string
	}{
		{
			name: "success",
			resp: &proxyv1.GetBacklogReviewResponse{
				Ceremony: testBacklogReviewProto(),
				Success:  true,
			},
			wantCeremonyID: "cer-br-1",
		},
		{
			name:       "server error",
			serverErr:  status.Error(codes.NotFound, "ceremony not found"),
			wantErr:    true,
			wantSubstr: "get_backlog_review RPC",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			client := startTestServer(t,
				&fakeCommandServer{},
				&fakeQueryServer{getBacklogReviewResp: tt.resp, getBacklogReviewErr: tt.serverErr},
			)

			got, err := client.GetBacklogReview(context.Background(), "cer-br-1")
			if tt.wantErr {
				if err == nil {
					t.Fatal("expected error, got nil")
				}
				if tt.wantSubstr != "" && !strings.Contains(err.Error(), tt.wantSubstr) {
					t.Errorf("error %q does not contain %q", err, tt.wantSubstr)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if got.CeremonyID != tt.wantCeremonyID {
				t.Errorf("CeremonyID = %q, want %q", got.CeremonyID, tt.wantCeremonyID)
			}
			if got.Status != "IN_PROGRESS" {
				t.Errorf("Status = %q, want %q", got.Status, "IN_PROGRESS")
			}
			if got.CreatedBy != "po-alice" {
				t.Errorf("CreatedBy = %q, want %q", got.CreatedBy, "po-alice")
			}
			if got.StartedAt != "2025-06-01T01:00:00Z" {
				t.Errorf("StartedAt = %q, want %q", got.StartedAt, "2025-06-01T01:00:00Z")
			}
		})
	}
}

// ===========================================================================
// Tests: ListBacklogReviews
// ===========================================================================

func TestFleetClient_ListBacklogReviews(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name       string
		resp       *proxyv1.ListBacklogReviewsResponse
		serverErr  error
		wantErr    bool
		wantSubstr string
		wantLen    int
	}{
		{
			name:    "empty list",
			resp:    &proxyv1.ListBacklogReviewsResponse{},
			wantLen: 0,
		},
		{
			name: "multiple backlog reviews",
			resp: &proxyv1.ListBacklogReviewsResponse{
				Ceremonies: []*proxyv1.BacklogReview{
					testBacklogReviewProto(),
					{
						CeremonyId: "cer-br-2",
						Status:     "COMPLETED",
						StoryIds:   []string{"s-3"},
						CreatedBy:  "po-bob",
						CreatedAt:  "2025-07-01T00:00:00Z",
						UpdatedAt:  "2025-07-02T00:00:00Z",
						CompletedAt: "2025-07-02T00:00:00Z",
					},
				},
				TotalCount: 2,
			},
			wantLen: 2,
		},
		{
			name:       "server error",
			serverErr:  status.Error(codes.Internal, "list failed"),
			wantErr:    true,
			wantSubstr: "list_backlog_reviews RPC",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			client := startTestServer(t,
				&fakeCommandServer{},
				&fakeQueryServer{listBacklogReviewsResp: tt.resp, listBacklogReviewsErr: tt.serverErr},
			)

			got, total, err := client.ListBacklogReviews(context.Background(), "", 100, 0)
			if tt.wantErr {
				if err == nil {
					t.Fatal("expected error, got nil")
				}
				if tt.wantSubstr != "" && !strings.Contains(err.Error(), tt.wantSubstr) {
					t.Errorf("error %q does not contain %q", err, tt.wantSubstr)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if len(got) != tt.wantLen {
				t.Fatalf("len = %d, want %d", len(got), tt.wantLen)
			}
			if tt.wantLen < 2 {
				return
			}
			if total != 2 {
				t.Errorf("totalCount = %d, want 2", total)
			}
			if got[0].CeremonyID != "cer-br-1" {
				t.Errorf("reviews[0].CeremonyID = %q, want %q", got[0].CeremonyID, "cer-br-1")
			}
			if got[1].CeremonyID != "cer-br-2" {
				t.Errorf("reviews[1].CeremonyID = %q, want %q", got[1].CeremonyID, "cer-br-2")
			}
			if got[1].Status != "COMPLETED" {
				t.Errorf("reviews[1].Status = %q, want %q", got[1].Status, "COMPLETED")
			}
			if got[1].CompletedAt != "2025-07-02T00:00:00Z" {
				t.Errorf("reviews[1].CompletedAt = %q, want %q", got[1].CompletedAt, "2025-07-02T00:00:00Z")
			}
		})
	}
}

// ===========================================================================
// Tests: ApproveReviewPlan
// ===========================================================================

func TestFleetClient_ApproveReviewPlan(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name           string
		resp           *proxyv1.ApproveReviewPlanResponse
		serverErr      error
		wantErr        bool
		wantSubstr     string
		wantCeremonyID string
		wantPlanID     string
	}{
		{
			name: "success",
			resp: &proxyv1.ApproveReviewPlanResponse{
				Ceremony: testBacklogReviewProto(),
				PlanId:   "plan-approved-1",
				Success:  true,
			},
			wantCeremonyID: "cer-br-1",
			wantPlanID:     "plan-approved-1",
		},
		{
			name:       "server error",
			serverErr:  status.Error(codes.FailedPrecondition, "story not in review"),
			wantErr:    true,
			wantSubstr: "approve_review_plan RPC",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			client := startTestServer(t,
				&fakeCommandServer{approveReviewPlanResp: tt.resp, approveReviewPlanErr: tt.serverErr},
				&fakeQueryServer{},
			)

			got, planID, err := client.ApproveReviewPlan(context.Background(), "req-1", "cer-br-1", "s-1", "looks good", "none", "high", "urgent feature")
			if tt.wantErr {
				if err == nil {
					t.Fatal("expected error, got nil")
				}
				if tt.wantSubstr != "" && !strings.Contains(err.Error(), tt.wantSubstr) {
					t.Errorf("error %q does not contain %q", err, tt.wantSubstr)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if got.CeremonyID != tt.wantCeremonyID {
				t.Errorf("CeremonyID = %q, want %q", got.CeremonyID, tt.wantCeremonyID)
			}
			if planID != tt.wantPlanID {
				t.Errorf("PlanID = %q, want %q", planID, tt.wantPlanID)
			}
		})
	}
}

// ===========================================================================
// Tests: RejectReviewPlan
// ===========================================================================

func TestFleetClient_RejectReviewPlan(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name           string
		resp           *proxyv1.RejectReviewPlanResponse
		serverErr      error
		wantErr        bool
		wantSubstr     string
		wantCeremonyID string
	}{
		{
			name: "success",
			resp: &proxyv1.RejectReviewPlanResponse{
				Ceremony: testBacklogReviewProto(),
				Success:  true,
			},
			wantCeremonyID: "cer-br-1",
		},
		{
			name:       "server error",
			serverErr:  status.Error(codes.FailedPrecondition, "story not in review"),
			wantErr:    true,
			wantSubstr: "reject_review_plan RPC",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			client := startTestServer(t,
				&fakeCommandServer{rejectReviewPlanResp: tt.resp, rejectReviewPlanErr: tt.serverErr},
				&fakeQueryServer{},
			)

			got, err := client.RejectReviewPlan(context.Background(), "req-1", "cer-br-1", "s-1", "plan lacks detail")
			if tt.wantErr {
				if err == nil {
					t.Fatal("expected error, got nil")
				}
				if tt.wantSubstr != "" && !strings.Contains(err.Error(), tt.wantSubstr) {
					t.Errorf("error %q does not contain %q", err, tt.wantSubstr)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if got.CeremonyID != tt.wantCeremonyID {
				t.Errorf("CeremonyID = %q, want %q", got.CeremonyID, tt.wantCeremonyID)
			}
		})
	}
}

// ===========================================================================
// Tests: CompleteBacklogReview
// ===========================================================================

func TestFleetClient_CompleteBacklogReview(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name           string
		resp           *proxyv1.CompleteBacklogReviewResponse
		serverErr      error
		wantErr        bool
		wantSubstr     string
		wantCeremonyID string
	}{
		{
			name: "success",
			resp: &proxyv1.CompleteBacklogReviewResponse{
				Ceremony: &proxyv1.BacklogReview{
					CeremonyId:  "cer-br-1",
					Status:      "COMPLETED",
					CompletedAt: "2025-06-10T00:00:00Z",
				},
				Success: true,
			},
			wantCeremonyID: "cer-br-1",
		},
		{
			name:       "server error",
			serverErr:  status.Error(codes.FailedPrecondition, "not all stories reviewed"),
			wantErr:    true,
			wantSubstr: "complete_backlog_review RPC",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			client := startTestServer(t,
				&fakeCommandServer{completeBacklogReviewResp: tt.resp, completeBacklogReviewErr: tt.serverErr},
				&fakeQueryServer{},
			)

			got, err := client.CompleteBacklogReview(context.Background(), "req-1", "cer-br-1")
			if tt.wantErr {
				if err == nil {
					t.Fatal("expected error, got nil")
				}
				if tt.wantSubstr != "" && !strings.Contains(err.Error(), tt.wantSubstr) {
					t.Errorf("error %q does not contain %q", err, tt.wantSubstr)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if got.CeremonyID != tt.wantCeremonyID {
				t.Errorf("CeremonyID = %q, want %q", got.CeremonyID, tt.wantCeremonyID)
			}
			if got.Status != "COMPLETED" {
				t.Errorf("Status = %q, want %q", got.Status, "COMPLETED")
			}
			if got.CompletedAt != "2025-06-10T00:00:00Z" {
				t.Errorf("CompletedAt = %q, want %q", got.CompletedAt, "2025-06-10T00:00:00Z")
			}
		})
	}
}

// ===========================================================================
// Tests: CancelBacklogReview
// ===========================================================================

func TestFleetClient_CancelBacklogReview(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name           string
		resp           *proxyv1.CancelBacklogReviewResponse
		serverErr      error
		wantErr        bool
		wantSubstr     string
		wantCeremonyID string
	}{
		{
			name: "success",
			resp: &proxyv1.CancelBacklogReviewResponse{
				Ceremony: &proxyv1.BacklogReview{
					CeremonyId: "cer-br-1",
					Status:     "CANCELLED",
				},
				Success: true,
			},
			wantCeremonyID: "cer-br-1",
		},
		{
			name:       "server error",
			serverErr:  status.Error(codes.FailedPrecondition, "ceremony already completed"),
			wantErr:    true,
			wantSubstr: "cancel_backlog_review RPC",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			client := startTestServer(t,
				&fakeCommandServer{cancelBacklogReviewResp: tt.resp, cancelBacklogReviewErr: tt.serverErr},
				&fakeQueryServer{},
			)

			got, err := client.CancelBacklogReview(context.Background(), "req-1", "cer-br-1")
			if tt.wantErr {
				if err == nil {
					t.Fatal("expected error, got nil")
				}
				if tt.wantSubstr != "" && !strings.Contains(err.Error(), tt.wantSubstr) {
					t.Errorf("error %q does not contain %q", err, tt.wantSubstr)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if got.CeremonyID != tt.wantCeremonyID {
				t.Errorf("CeremonyID = %q, want %q", got.CeremonyID, tt.wantCeremonyID)
			}
			if got.Status != "CANCELLED" {
				t.Errorf("Status = %q, want %q", got.Status, "CANCELLED")
			}
		})
	}
}

// ===========================================================================
// Tests: Enroll
// ===========================================================================

func TestFleetClient_Enroll(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name       string
		resp       *proxyv1.EnrollResponse
		serverErr  error
		wantErr    bool
		wantSubstr string
	}{
		{
			name: "success",
			resp: &proxyv1.EnrollResponse{
				ClientCertPem: []byte("-----BEGIN CERTIFICATE-----\nfake-cert\n-----END CERTIFICATE-----\n"),
				CaChainPem:    []byte("-----BEGIN CERTIFICATE-----\nfake-ca\n-----END CERTIFICATE-----\n"),
				ClientId:      "spiffe://fleet/device/dev-001",
				ExpiresAt:     "2026-01-01T00:00:00Z",
			},
		},
		{
			name:       "server error",
			serverErr:  status.Error(codes.Unauthenticated, "invalid API key"),
			wantErr:    true,
			wantSubstr: "enroll RPC",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			client := startTestServerFull(t,
				&fakeCommandServer{},
				&fakeQueryServer{},
				&fakeEnrollmentServer{enrollResp: tt.resp, enrollErr: tt.serverErr},
			)

			certPEM, caPEM, clientID, expiresAt, err := client.Enroll(context.Background(), "api-key-123", "dev-001", []byte("fake-csr"))
			if tt.wantErr {
				if err == nil {
					t.Fatal("expected error, got nil")
				}
				if tt.wantSubstr != "" && !strings.Contains(err.Error(), tt.wantSubstr) {
					t.Errorf("error %q does not contain %q", err, tt.wantSubstr)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if !strings.Contains(string(certPEM), "fake-cert") {
				t.Errorf("certPEM does not contain expected content: %q", string(certPEM))
			}
			if !strings.Contains(string(caPEM), "fake-ca") {
				t.Errorf("caPEM does not contain expected content: %q", string(caPEM))
			}
			if clientID != "spiffe://fleet/device/dev-001" {
				t.Errorf("clientID = %q, want %q", clientID, "spiffe://fleet/device/dev-001")
			}
			if expiresAt != "2026-01-01T00:00:00Z" {
				t.Errorf("expiresAt = %q, want %q", expiresAt, "2026-01-01T00:00:00Z")
			}
		})
	}
}

// ===========================================================================
// Tests: Renew
// ===========================================================================

func TestFleetClient_Renew(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name       string
		resp       *proxyv1.RenewResponse
		serverErr  error
		wantErr    bool
		wantSubstr string
	}{
		{
			name: "success",
			resp: &proxyv1.RenewResponse{
				ClientCertPem: []byte("-----BEGIN CERTIFICATE-----\nnew-cert\n-----END CERTIFICATE-----\n"),
				CaChainPem:    []byte("-----BEGIN CERTIFICATE-----\nnew-ca\n-----END CERTIFICATE-----\n"),
				ExpiresAt:     "2027-01-01T00:00:00Z",
			},
		},
		{
			name:       "server error",
			serverErr:  status.Error(codes.Unauthenticated, "certificate expired"),
			wantErr:    true,
			wantSubstr: "renew RPC",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			client := startTestServerFull(t,
				&fakeCommandServer{},
				&fakeQueryServer{},
				&fakeEnrollmentServer{renewResp: tt.resp, renewErr: tt.serverErr},
			)

			certPEM, caPEM, expiresAt, err := client.Renew(context.Background(), []byte("fake-csr"))
			if tt.wantErr {
				if err == nil {
					t.Fatal("expected error, got nil")
				}
				if tt.wantSubstr != "" && !strings.Contains(err.Error(), tt.wantSubstr) {
					t.Errorf("error %q does not contain %q", err, tt.wantSubstr)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if !strings.Contains(string(certPEM), "new-cert") {
				t.Errorf("certPEM does not contain expected content: %q", string(certPEM))
			}
			if !strings.Contains(string(caPEM), "new-ca") {
				t.Errorf("caPEM does not contain expected content: %q", string(caPEM))
			}
			if expiresAt != "2027-01-01T00:00:00Z" {
				t.Errorf("expiresAt = %q, want %q", expiresAt, "2027-01-01T00:00:00Z")
			}
		})
	}
}
