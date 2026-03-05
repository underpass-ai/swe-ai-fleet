package planning

import (
	"context"
	"fmt"
	"net"
	"testing"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/status"
	"google.golang.org/grpc/test/bufconn"

	pb "github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/gen/planningv2"
)

// ---------------------------------------------------------------------------
// Fake planning gRPC server — configurable per-method responses
// ---------------------------------------------------------------------------

type fakePlanningServer struct {
	pb.UnimplementedPlanningServiceServer

	// CreateProject
	createProjectResp *pb.CreateProjectResponse
	createProjectErr  error

	// CreateEpic
	createEpicResp *pb.CreateEpicResponse
	createEpicErr  error

	// CreateStory
	createStoryResp *pb.CreateStoryResponse
	createStoryErr  error

	// TransitionStory
	transitionStoryResp *pb.TransitionStoryResponse
	transitionStoryErr  error

	// CreateTask
	createTaskResp *pb.CreateTaskResponse
	createTaskErr  error

	// ApproveDecision
	approveDecisionResp *pb.ApproveDecisionResponse
	approveDecisionErr  error

	// RejectDecision
	rejectDecisionResp *pb.RejectDecisionResponse
	rejectDecisionErr  error

	// ListProjects
	listProjectsResp *pb.ListProjectsResponse
	listProjectsErr  error

	// ListEpics
	listEpicsResp *pb.ListEpicsResponse
	listEpicsErr  error

	// ListStories
	listStoriesResp *pb.ListStoriesResponse
	listStoriesErr  error

	// ListTasks
	listTasksResp *pb.ListTasksResponse
	listTasksErr  error

	// CreateBacklogReviewCeremony
	createBacklogReviewResp *pb.CreateBacklogReviewCeremonyResponse
	createBacklogReviewErr  error

	// StartBacklogReviewCeremony
	startBacklogReviewResp *pb.StartBacklogReviewCeremonyResponse
	startBacklogReviewErr  error

	// GetBacklogReviewCeremony
	getBacklogReviewResp *pb.BacklogReviewCeremonyResponse
	getBacklogReviewErr  error

	// ListBacklogReviewCeremonies
	listBacklogReviewsResp *pb.ListBacklogReviewCeremoniesResponse
	listBacklogReviewsErr  error

	// ApproveReviewPlan
	approveReviewPlanResp *pb.ApproveReviewPlanResponse
	approveReviewPlanErr  error

	// RejectReviewPlan
	rejectReviewPlanResp *pb.RejectReviewPlanResponse
	rejectReviewPlanErr  error

	// CompleteBacklogReviewCeremony
	completeBacklogReviewResp *pb.CompleteBacklogReviewCeremonyResponse
	completeBacklogReviewErr  error

	// CancelBacklogReviewCeremony
	cancelBacklogReviewResp *pb.CancelBacklogReviewCeremonyResponse
	cancelBacklogReviewErr  error
}

func (f *fakePlanningServer) CreateProject(_ context.Context, _ *pb.CreateProjectRequest) (*pb.CreateProjectResponse, error) {
	return f.createProjectResp, f.createProjectErr
}

func (f *fakePlanningServer) CreateEpic(_ context.Context, _ *pb.CreateEpicRequest) (*pb.CreateEpicResponse, error) {
	return f.createEpicResp, f.createEpicErr
}

func (f *fakePlanningServer) CreateStory(_ context.Context, _ *pb.CreateStoryRequest) (*pb.CreateStoryResponse, error) {
	return f.createStoryResp, f.createStoryErr
}

func (f *fakePlanningServer) TransitionStory(_ context.Context, _ *pb.TransitionStoryRequest) (*pb.TransitionStoryResponse, error) {
	return f.transitionStoryResp, f.transitionStoryErr
}

func (f *fakePlanningServer) CreateTask(_ context.Context, _ *pb.CreateTaskRequest) (*pb.CreateTaskResponse, error) {
	return f.createTaskResp, f.createTaskErr
}

func (f *fakePlanningServer) ApproveDecision(_ context.Context, _ *pb.ApproveDecisionRequest) (*pb.ApproveDecisionResponse, error) {
	return f.approveDecisionResp, f.approveDecisionErr
}

func (f *fakePlanningServer) RejectDecision(_ context.Context, _ *pb.RejectDecisionRequest) (*pb.RejectDecisionResponse, error) {
	return f.rejectDecisionResp, f.rejectDecisionErr
}

func (f *fakePlanningServer) ListProjects(_ context.Context, _ *pb.ListProjectsRequest) (*pb.ListProjectsResponse, error) {
	return f.listProjectsResp, f.listProjectsErr
}

func (f *fakePlanningServer) ListEpics(_ context.Context, _ *pb.ListEpicsRequest) (*pb.ListEpicsResponse, error) {
	return f.listEpicsResp, f.listEpicsErr
}

func (f *fakePlanningServer) ListStories(_ context.Context, _ *pb.ListStoriesRequest) (*pb.ListStoriesResponse, error) {
	return f.listStoriesResp, f.listStoriesErr
}

func (f *fakePlanningServer) ListTasks(_ context.Context, _ *pb.ListTasksRequest) (*pb.ListTasksResponse, error) {
	return f.listTasksResp, f.listTasksErr
}

func (f *fakePlanningServer) CreateBacklogReviewCeremony(_ context.Context, _ *pb.CreateBacklogReviewCeremonyRequest) (*pb.CreateBacklogReviewCeremonyResponse, error) {
	return f.createBacklogReviewResp, f.createBacklogReviewErr
}

func (f *fakePlanningServer) StartBacklogReviewCeremony(_ context.Context, _ *pb.StartBacklogReviewCeremonyRequest) (*pb.StartBacklogReviewCeremonyResponse, error) {
	return f.startBacklogReviewResp, f.startBacklogReviewErr
}

func (f *fakePlanningServer) GetBacklogReviewCeremony(_ context.Context, _ *pb.GetBacklogReviewCeremonyRequest) (*pb.BacklogReviewCeremonyResponse, error) {
	return f.getBacklogReviewResp, f.getBacklogReviewErr
}

func (f *fakePlanningServer) ListBacklogReviewCeremonies(_ context.Context, _ *pb.ListBacklogReviewCeremoniesRequest) (*pb.ListBacklogReviewCeremoniesResponse, error) {
	return f.listBacklogReviewsResp, f.listBacklogReviewsErr
}

func (f *fakePlanningServer) ApproveReviewPlan(_ context.Context, _ *pb.ApproveReviewPlanRequest) (*pb.ApproveReviewPlanResponse, error) {
	return f.approveReviewPlanResp, f.approveReviewPlanErr
}

func (f *fakePlanningServer) RejectReviewPlan(_ context.Context, _ *pb.RejectReviewPlanRequest) (*pb.RejectReviewPlanResponse, error) {
	return f.rejectReviewPlanResp, f.rejectReviewPlanErr
}

func (f *fakePlanningServer) CompleteBacklogReviewCeremony(_ context.Context, _ *pb.CompleteBacklogReviewCeremonyRequest) (*pb.CompleteBacklogReviewCeremonyResponse, error) {
	return f.completeBacklogReviewResp, f.completeBacklogReviewErr
}

func (f *fakePlanningServer) CancelBacklogReviewCeremony(_ context.Context, _ *pb.CancelBacklogReviewCeremonyRequest) (*pb.CancelBacklogReviewCeremonyResponse, error) {
	return f.cancelBacklogReviewResp, f.cancelBacklogReviewErr
}

// ---------------------------------------------------------------------------
// Test harness: spins up a bufconn-based gRPC server with the fake,
// and returns a Client connected to it.
// ---------------------------------------------------------------------------

func setupBufconn(t *testing.T, fake *fakePlanningServer) *Client {
	t.Helper()
	const bufSize = 1024 * 1024
	lis := bufconn.Listen(bufSize)

	srv := grpc.NewServer()
	pb.RegisterPlanningServiceServer(srv, fake)

	go func() {
		if err := srv.Serve(lis); err != nil {
			// Server stopped — expected during cleanup.
		}
	}()
	t.Cleanup(func() {
		srv.Stop()
		lis.Close()
	})

	conn, err := grpc.NewClient(
		"passthrough:///bufconn",
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithContextDialer(func(_ context.Context, _ string) (net.Conn, error) {
			return lis.Dial()
		}),
	)
	if err != nil {
		t.Fatalf("dial bufconn: %v", err)
	}
	t.Cleanup(func() { conn.Close() })

	return &Client{
		conn: conn,
		rpc:  pb.NewPlanningServiceClient(conn),
	}
}

// ---------------------------------------------------------------------------
// CreateProject
// ---------------------------------------------------------------------------

func TestCreateProject_Success(t *testing.T) {
	fake := &fakePlanningServer{
		createProjectResp: &pb.CreateProjectResponse{
			Project: &pb.Project{ProjectId: "proj-1", Name: "TestProject"},
		},
	}
	c := setupBufconn(t, fake)

	id, err := c.CreateProject(context.Background(), "TestProject", "desc", "alice")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if id != "proj-1" {
		t.Fatalf("got id=%q, want %q", id, "proj-1")
	}
}

func TestCreateProject_RPCError(t *testing.T) {
	fake := &fakePlanningServer{
		createProjectErr: status.Error(codes.Internal, "boom"),
	}
	c := setupBufconn(t, fake)

	_, err := c.CreateProject(context.Background(), "P", "d", "u")
	if err == nil {
		t.Fatal("expected error, got nil")
	}
}

func TestCreateProject_NilProject(t *testing.T) {
	fake := &fakePlanningServer{
		createProjectResp: &pb.CreateProjectResponse{Project: nil},
	}
	c := setupBufconn(t, fake)

	_, err := c.CreateProject(context.Background(), "P", "d", "u")
	if err == nil {
		t.Fatal("expected error for nil project, got nil")
	}
}

// ---------------------------------------------------------------------------
// CreateEpic
// ---------------------------------------------------------------------------

func TestCreateEpic_Success(t *testing.T) {
	fake := &fakePlanningServer{
		createEpicResp: &pb.CreateEpicResponse{
			Epic: &pb.Epic{EpicId: "epic-1", ProjectId: "proj-1", Title: "E1"},
		},
	}
	c := setupBufconn(t, fake)

	id, err := c.CreateEpic(context.Background(), "proj-1", "E1", "desc")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if id != "epic-1" {
		t.Fatalf("got id=%q, want %q", id, "epic-1")
	}
}

func TestCreateEpic_RPCError(t *testing.T) {
	fake := &fakePlanningServer{
		createEpicErr: status.Error(codes.NotFound, "project not found"),
	}
	c := setupBufconn(t, fake)

	_, err := c.CreateEpic(context.Background(), "proj-x", "E", "d")
	if err == nil {
		t.Fatal("expected error, got nil")
	}
}

func TestCreateEpic_NilEpic(t *testing.T) {
	fake := &fakePlanningServer{
		createEpicResp: &pb.CreateEpicResponse{Epic: nil},
	}
	c := setupBufconn(t, fake)

	_, err := c.CreateEpic(context.Background(), "p", "E", "d")
	if err == nil {
		t.Fatal("expected error for nil epic, got nil")
	}
}

// ---------------------------------------------------------------------------
// CreateStory
// ---------------------------------------------------------------------------

func TestCreateStory_Success(t *testing.T) {
	fake := &fakePlanningServer{
		createStoryResp: &pb.CreateStoryResponse{
			Story: &pb.Story{StoryId: "story-1", EpicId: "epic-1", Title: "S1"},
		},
	}
	c := setupBufconn(t, fake)

	id, err := c.CreateStory(context.Background(), "epic-1", "S1", "brief", "alice")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if id != "story-1" {
		t.Fatalf("got id=%q, want %q", id, "story-1")
	}
}

func TestCreateStory_RPCError(t *testing.T) {
	fake := &fakePlanningServer{
		createStoryErr: status.Error(codes.InvalidArgument, "bad"),
	}
	c := setupBufconn(t, fake)

	_, err := c.CreateStory(context.Background(), "e", "S", "b", "u")
	if err == nil {
		t.Fatal("expected error, got nil")
	}
}

func TestCreateStory_NilStory(t *testing.T) {
	fake := &fakePlanningServer{
		createStoryResp: &pb.CreateStoryResponse{Story: nil},
	}
	c := setupBufconn(t, fake)

	_, err := c.CreateStory(context.Background(), "e", "S", "b", "u")
	if err == nil {
		t.Fatal("expected error for nil story, got nil")
	}
}

// ---------------------------------------------------------------------------
// TransitionStory
// ---------------------------------------------------------------------------

func TestTransitionStory_Success(t *testing.T) {
	fake := &fakePlanningServer{
		transitionStoryResp: &pb.TransitionStoryResponse{Success: true},
	}
	c := setupBufconn(t, fake)

	err := c.TransitionStory(context.Background(), "story-1", "IN_PROGRESS")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestTransitionStory_RPCError(t *testing.T) {
	fake := &fakePlanningServer{
		transitionStoryErr: status.Error(codes.FailedPrecondition, "invalid transition"),
	}
	c := setupBufconn(t, fake)

	err := c.TransitionStory(context.Background(), "story-1", "DONE")
	if err == nil {
		t.Fatal("expected error, got nil")
	}
}

// ---------------------------------------------------------------------------
// CreateTask
// ---------------------------------------------------------------------------

func TestCreateTask_Success(t *testing.T) {
	fake := &fakePlanningServer{
		createTaskResp: &pb.CreateTaskResponse{
			Task: &pb.Task{TaskId: "task-1", StoryId: "story-1", Title: "T1"},
		},
	}
	c := setupBufconn(t, fake)

	id, err := c.CreateTask(context.Background(), "req-1", "story-1", "T1", "desc", "development", "agent-1", 4, 1)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if id != "task-1" {
		t.Fatalf("got id=%q, want %q", id, "task-1")
	}
}

func TestCreateTask_RPCError(t *testing.T) {
	fake := &fakePlanningServer{
		createTaskErr: status.Error(codes.Internal, "db error"),
	}
	c := setupBufconn(t, fake)

	_, err := c.CreateTask(context.Background(), "req-1", "story-1", "T", "d", "dev", "a", 1, 1)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
}

func TestCreateTask_NilTask(t *testing.T) {
	fake := &fakePlanningServer{
		createTaskResp: &pb.CreateTaskResponse{Task: nil},
	}
	c := setupBufconn(t, fake)

	_, err := c.CreateTask(context.Background(), "req-1", "story-1", "T", "d", "dev", "a", 1, 1)
	if err == nil {
		t.Fatal("expected error for nil task, got nil")
	}
}

// ---------------------------------------------------------------------------
// ApproveDecision
// ---------------------------------------------------------------------------

func TestApproveDecision_Success(t *testing.T) {
	fake := &fakePlanningServer{
		approveDecisionResp: &pb.ApproveDecisionResponse{Success: true},
	}
	c := setupBufconn(t, fake)

	err := c.ApproveDecision(context.Background(), "story-1", "dec-1", "alice", "looks good")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestApproveDecision_RPCError(t *testing.T) {
	fake := &fakePlanningServer{
		approveDecisionErr: status.Error(codes.NotFound, "decision not found"),
	}
	c := setupBufconn(t, fake)

	err := c.ApproveDecision(context.Background(), "s", "d", "u", "c")
	if err == nil {
		t.Fatal("expected error, got nil")
	}
}

// ---------------------------------------------------------------------------
// RejectDecision
// ---------------------------------------------------------------------------

func TestRejectDecision_Success(t *testing.T) {
	fake := &fakePlanningServer{
		rejectDecisionResp: &pb.RejectDecisionResponse{Success: true},
	}
	c := setupBufconn(t, fake)

	err := c.RejectDecision(context.Background(), "story-1", "dec-1", "bob", "needs work")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestRejectDecision_RPCError(t *testing.T) {
	fake := &fakePlanningServer{
		rejectDecisionErr: status.Error(codes.PermissionDenied, "not authorized"),
	}
	c := setupBufconn(t, fake)

	err := c.RejectDecision(context.Background(), "s", "d", "u", "r")
	if err == nil {
		t.Fatal("expected error, got nil")
	}
}

// ---------------------------------------------------------------------------
// ListProjects
// ---------------------------------------------------------------------------

func TestListProjects_Success(t *testing.T) {
	fake := &fakePlanningServer{
		listProjectsResp: &pb.ListProjectsResponse{
			Projects: []*pb.Project{
				{ProjectId: "p1", Name: "Alpha", Description: "first", Status: "active", Owner: "alice", CreatedAt: "2025-01-01", UpdatedAt: "2025-01-02"},
				{ProjectId: "p2", Name: "Beta", Description: "second", Status: "planning", Owner: "bob", CreatedAt: "2025-02-01", UpdatedAt: "2025-02-02"},
			},
			TotalCount: 5,
		},
	}
	c := setupBufconn(t, fake)

	projects, total, err := c.ListProjects(context.Background(), "active", 10, 0)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if total != 5 {
		t.Fatalf("got total=%d, want 5", total)
	}
	if len(projects) != 2 {
		t.Fatalf("got %d projects, want 2", len(projects))
	}
	if projects[0].ProjectID != "p1" {
		t.Fatalf("got ProjectID=%q, want %q", projects[0].ProjectID, "p1")
	}
	if projects[0].Name != "Alpha" {
		t.Fatalf("got Name=%q, want %q", projects[0].Name, "Alpha")
	}
	if projects[0].Owner != "alice" {
		t.Fatalf("got Owner=%q, want %q", projects[0].Owner, "alice")
	}
	if projects[1].ProjectID != "p2" {
		t.Fatalf("got ProjectID=%q, want %q", projects[1].ProjectID, "p2")
	}
}

func TestListProjects_RPCError(t *testing.T) {
	fake := &fakePlanningServer{
		listProjectsErr: status.Error(codes.Unavailable, "service down"),
	}
	c := setupBufconn(t, fake)

	_, _, err := c.ListProjects(context.Background(), "", 10, 0)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
}

func TestListProjects_Empty(t *testing.T) {
	fake := &fakePlanningServer{
		listProjectsResp: &pb.ListProjectsResponse{
			Projects:   nil,
			TotalCount: 0,
		},
	}
	c := setupBufconn(t, fake)

	projects, total, err := c.ListProjects(context.Background(), "", 10, 0)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if total != 0 {
		t.Fatalf("got total=%d, want 0", total)
	}
	if len(projects) != 0 {
		t.Fatalf("got %d projects, want 0", len(projects))
	}
}

// ---------------------------------------------------------------------------
// ListEpics
// ---------------------------------------------------------------------------

func TestListEpics_Success(t *testing.T) {
	fake := &fakePlanningServer{
		listEpicsResp: &pb.ListEpicsResponse{
			Epics: []*pb.Epic{
				{EpicId: "e1", ProjectId: "p1", Title: "Epic One", Description: "first", Status: "active", CreatedAt: "2025-01-01", UpdatedAt: "2025-01-02"},
			},
			TotalCount: 1,
		},
	}
	c := setupBufconn(t, fake)

	epics, total, err := c.ListEpics(context.Background(), "p1", "active", 10, 0)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if total != 1 {
		t.Fatalf("got total=%d, want 1", total)
	}
	if len(epics) != 1 {
		t.Fatalf("got %d epics, want 1", len(epics))
	}
	if epics[0].EpicID != "e1" {
		t.Fatalf("got EpicID=%q, want %q", epics[0].EpicID, "e1")
	}
	if epics[0].ProjectID != "p1" {
		t.Fatalf("got ProjectID=%q, want %q", epics[0].ProjectID, "p1")
	}
}

func TestListEpics_RPCError(t *testing.T) {
	fake := &fakePlanningServer{
		listEpicsErr: status.Error(codes.Internal, "fail"),
	}
	c := setupBufconn(t, fake)

	_, _, err := c.ListEpics(context.Background(), "p1", "", 10, 0)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
}

// ---------------------------------------------------------------------------
// ListStories
// ---------------------------------------------------------------------------

func TestListStories_Success(t *testing.T) {
	fake := &fakePlanningServer{
		listStoriesResp: &pb.ListStoriesResponse{
			Stories: []*pb.Story{
				{StoryId: "s1", EpicId: "e1", Title: "Story One", Brief: "brief", State: "DRAFT", DorScore: 75, CreatedBy: "alice", CreatedAt: "2025-01-01", UpdatedAt: "2025-01-02"},
			},
			TotalCount: 3,
		},
	}
	c := setupBufconn(t, fake)

	stories, total, err := c.ListStories(context.Background(), "e1", "DRAFT", 10, 0)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if total != 3 {
		t.Fatalf("got total=%d, want 3", total)
	}
	if len(stories) != 1 {
		t.Fatalf("got %d stories, want 1", len(stories))
	}
	if stories[0].StoryID != "s1" {
		t.Fatalf("got StoryID=%q, want %q", stories[0].StoryID, "s1")
	}
	if stories[0].DorScore != 75 {
		t.Fatalf("got DorScore=%d, want 75", stories[0].DorScore)
	}
	if stories[0].CreatedBy != "alice" {
		t.Fatalf("got CreatedBy=%q, want %q", stories[0].CreatedBy, "alice")
	}
}

func TestListStories_RPCError(t *testing.T) {
	fake := &fakePlanningServer{
		listStoriesErr: status.Error(codes.Internal, "fail"),
	}
	c := setupBufconn(t, fake)

	_, _, err := c.ListStories(context.Background(), "e1", "", 10, 0)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
}

// ---------------------------------------------------------------------------
// ListTasks
// ---------------------------------------------------------------------------

func TestListTasks_Success(t *testing.T) {
	fake := &fakePlanningServer{
		listTasksResp: &pb.ListTasksResponse{
			Tasks: []*pb.Task{
				{TaskId: "t1", StoryId: "s1", Title: "Task One", Description: "do it", Type: "development", Status: "todo", AssignedTo: "agent-1", EstimatedHours: 4, Priority: 1, CreatedAt: "2025-01-01", UpdatedAt: "2025-01-02"},
				{TaskId: "t2", StoryId: "s1", Title: "Task Two", Description: "test it", Type: "testing", Status: "in_progress", AssignedTo: "agent-2", EstimatedHours: 2, Priority: 2, CreatedAt: "2025-01-03", UpdatedAt: "2025-01-04"},
			},
			TotalCount: 10,
		},
	}
	c := setupBufconn(t, fake)

	tasks, total, err := c.ListTasks(context.Background(), "s1", "todo", 10, 0)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if total != 10 {
		t.Fatalf("got total=%d, want 10", total)
	}
	if len(tasks) != 2 {
		t.Fatalf("got %d tasks, want 2", len(tasks))
	}
	if tasks[0].TaskID != "t1" {
		t.Fatalf("got TaskID=%q, want %q", tasks[0].TaskID, "t1")
	}
	if tasks[0].EstimatedHours != 4 {
		t.Fatalf("got EstimatedHours=%d, want 4", tasks[0].EstimatedHours)
	}
	if tasks[1].AssignedTo != "agent-2" {
		t.Fatalf("got AssignedTo=%q, want %q", tasks[1].AssignedTo, "agent-2")
	}
}

func TestListTasks_RPCError(t *testing.T) {
	fake := &fakePlanningServer{
		listTasksErr: status.Error(codes.Internal, "fail"),
	}
	c := setupBufconn(t, fake)

	_, _, err := c.ListTasks(context.Background(), "s1", "", 10, 0)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
}

// ---------------------------------------------------------------------------
// CreateBacklogReview
// ---------------------------------------------------------------------------

func TestCreateBacklogReview_Success(t *testing.T) {
	fake := &fakePlanningServer{
		createBacklogReviewResp: &pb.CreateBacklogReviewCeremonyResponse{
			Ceremony: &pb.BacklogReviewCeremony{
				CeremonyId: "cer-1",
				Status:     "DRAFT",
				CreatedBy:  "alice",
				StoryIds:   []string{"s1", "s2"},
				CreatedAt:  "2025-03-01",
				UpdatedAt:  "2025-03-01",
			},
		},
	}
	c := setupBufconn(t, fake)

	result, err := c.CreateBacklogReview(context.Background(), "alice", []string{"s1", "s2"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.CeremonyID != "cer-1" {
		t.Fatalf("got CeremonyID=%q, want %q", result.CeremonyID, "cer-1")
	}
	if result.Status != "DRAFT" {
		t.Fatalf("got Status=%q, want %q", result.Status, "DRAFT")
	}
	if len(result.StoryIDs) != 2 {
		t.Fatalf("got %d StoryIDs, want 2", len(result.StoryIDs))
	}
}

func TestCreateBacklogReview_RPCError(t *testing.T) {
	fake := &fakePlanningServer{
		createBacklogReviewErr: status.Error(codes.InvalidArgument, "empty stories"),
	}
	c := setupBufconn(t, fake)

	_, err := c.CreateBacklogReview(context.Background(), "alice", nil)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
}

// ---------------------------------------------------------------------------
// StartBacklogReview
// ---------------------------------------------------------------------------

func TestStartBacklogReview_Success(t *testing.T) {
	fake := &fakePlanningServer{
		startBacklogReviewResp: &pb.StartBacklogReviewCeremonyResponse{
			Ceremony: &pb.BacklogReviewCeremony{
				CeremonyId: "cer-1",
				Status:     "IN_PROGRESS",
				CreatedBy:  "alice",
			},
			TotalDeliberationsSubmitted: 6,
		},
	}
	c := setupBufconn(t, fake)

	result, count, err := c.StartBacklogReview(context.Background(), "cer-1", "alice")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.CeremonyID != "cer-1" {
		t.Fatalf("got CeremonyID=%q, want %q", result.CeremonyID, "cer-1")
	}
	if result.Status != "IN_PROGRESS" {
		t.Fatalf("got Status=%q, want %q", result.Status, "IN_PROGRESS")
	}
	if count != 6 {
		t.Fatalf("got count=%d, want 6", count)
	}
}

func TestStartBacklogReview_RPCError(t *testing.T) {
	fake := &fakePlanningServer{
		startBacklogReviewErr: status.Error(codes.FailedPrecondition, "not draft"),
	}
	c := setupBufconn(t, fake)

	_, _, err := c.StartBacklogReview(context.Background(), "cer-1", "alice")
	if err == nil {
		t.Fatal("expected error, got nil")
	}
}

// ---------------------------------------------------------------------------
// GetBacklogReview
// ---------------------------------------------------------------------------

func TestGetBacklogReview_Success(t *testing.T) {
	startedAt := "2025-03-01T10:00:00Z"
	fake := &fakePlanningServer{
		getBacklogReviewResp: &pb.BacklogReviewCeremonyResponse{
			Ceremony: &pb.BacklogReviewCeremony{
				CeremonyId: "cer-1",
				Status:     "REVIEWING",
				CreatedBy:  "alice",
				StoryIds:   []string{"s1"},
				StartedAt:  &startedAt,
				ReviewResults: []*pb.StoryReviewResult{
					{
						StoryId:           "s1",
						ArchitectFeedback: "solid arch",
						QaFeedback:        "tests ok",
						DevopsFeedback:    "deploy ready",
						ApprovalStatus:    "PENDING",
						Recommendations:   []string{"add caching"},
						PlanPreliminary: &pb.PlanPreliminary{
							Title:               "Plan for S1",
							Description:         "desc",
							TechnicalNotes:      "notes",
							EstimatedComplexity: "MEDIUM",
							AcceptanceCriteria:  []string{"criterion 1"},
							Roles:               []string{"developer"},
							Dependencies:        []string{"db migration"},
							TasksOutline:        []string{"implement", "test"},
						},
					},
				},
			},
		},
	}
	c := setupBufconn(t, fake)

	result, err := c.GetBacklogReview(context.Background(), "cer-1")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.CeremonyID != "cer-1" {
		t.Fatalf("got CeremonyID=%q, want %q", result.CeremonyID, "cer-1")
	}
	if result.StartedAt != startedAt {
		t.Fatalf("got StartedAt=%q, want %q", result.StartedAt, startedAt)
	}
	if len(result.ReviewResults) != 1 {
		t.Fatalf("got %d ReviewResults, want 1", len(result.ReviewResults))
	}
	rr := result.ReviewResults[0]
	if rr.StoryID != "s1" {
		t.Fatalf("got StoryID=%q, want %q", rr.StoryID, "s1")
	}
	if rr.ArchitectFeedback != "solid arch" {
		t.Fatalf("got ArchitectFeedback=%q, want %q", rr.ArchitectFeedback, "solid arch")
	}
	if rr.PlanPreliminary.Title != "Plan for S1" {
		t.Fatalf("got PlanPreliminary.Title=%q, want %q", rr.PlanPreliminary.Title, "Plan for S1")
	}
	if rr.PlanPreliminary.EstimatedComplexity != "MEDIUM" {
		t.Fatalf("got PlanPreliminary.EstimatedComplexity=%q, want %q", rr.PlanPreliminary.EstimatedComplexity, "MEDIUM")
	}
	if len(rr.Recommendations) != 1 || rr.Recommendations[0] != "add caching" {
		t.Fatalf("got Recommendations=%v, want [add caching]", rr.Recommendations)
	}
}

func TestGetBacklogReview_RPCError(t *testing.T) {
	fake := &fakePlanningServer{
		getBacklogReviewErr: status.Error(codes.NotFound, "not found"),
	}
	c := setupBufconn(t, fake)

	_, err := c.GetBacklogReview(context.Background(), "cer-x")
	if err == nil {
		t.Fatal("expected error, got nil")
	}
}

// ---------------------------------------------------------------------------
// ListBacklogReviews
// ---------------------------------------------------------------------------

func TestListBacklogReviews_Success(t *testing.T) {
	fake := &fakePlanningServer{
		listBacklogReviewsResp: &pb.ListBacklogReviewCeremoniesResponse{
			Ceremonies: []*pb.BacklogReviewCeremony{
				{CeremonyId: "cer-1", Status: "COMPLETED", CreatedBy: "alice"},
				{CeremonyId: "cer-2", Status: "DRAFT", CreatedBy: "bob"},
			},
			TotalCount: 2,
		},
	}
	c := setupBufconn(t, fake)

	results, total, err := c.ListBacklogReviews(context.Background(), "COMPLETED", 10, 0)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if total != 2 {
		t.Fatalf("got total=%d, want 2", total)
	}
	if len(results) != 2 {
		t.Fatalf("got %d results, want 2", len(results))
	}
}

func TestListBacklogReviews_EmptyFilter(t *testing.T) {
	fake := &fakePlanningServer{
		listBacklogReviewsResp: &pb.ListBacklogReviewCeremoniesResponse{
			Ceremonies: []*pb.BacklogReviewCeremony{
				{CeremonyId: "cer-1", Status: "DRAFT"},
			},
			TotalCount: 1,
		},
	}
	c := setupBufconn(t, fake)

	// Empty status filter should not set StatusFilter on request.
	results, total, err := c.ListBacklogReviews(context.Background(), "", 10, 0)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if total != 1 {
		t.Fatalf("got total=%d, want 1", total)
	}
	if len(results) != 1 {
		t.Fatalf("got %d results, want 1", len(results))
	}
}

func TestListBacklogReviews_RPCError(t *testing.T) {
	fake := &fakePlanningServer{
		listBacklogReviewsErr: status.Error(codes.Internal, "fail"),
	}
	c := setupBufconn(t, fake)

	_, _, err := c.ListBacklogReviews(context.Background(), "", 10, 0)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
}

// ---------------------------------------------------------------------------
// ApproveReviewPlan
// ---------------------------------------------------------------------------

func TestApproveReviewPlan_Success(t *testing.T) {
	fake := &fakePlanningServer{
		approveReviewPlanResp: &pb.ApproveReviewPlanResponse{
			Ceremony: &pb.BacklogReviewCeremony{
				CeremonyId: "cer-1",
				Status:     "REVIEWING",
			},
			PlanId: "plan-42",
		},
	}
	c := setupBufconn(t, fake)

	result, planID, err := c.ApproveReviewPlan(context.Background(), "cer-1", "s1", "alice", "ship it", "watch perf", "HIGH", "critical path")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.CeremonyID != "cer-1" {
		t.Fatalf("got CeremonyID=%q, want %q", result.CeremonyID, "cer-1")
	}
	if planID != "plan-42" {
		t.Fatalf("got planID=%q, want %q", planID, "plan-42")
	}
}

func TestApproveReviewPlan_OptionalFieldsEmpty(t *testing.T) {
	fake := &fakePlanningServer{
		approveReviewPlanResp: &pb.ApproveReviewPlanResponse{
			Ceremony: &pb.BacklogReviewCeremony{
				CeremonyId: "cer-1",
				Status:     "REVIEWING",
			},
			PlanId: "plan-43",
		},
	}
	c := setupBufconn(t, fake)

	// Empty optional fields (poConcerns, priorityAdj, prioReason) should be omitted.
	result, planID, err := c.ApproveReviewPlan(context.Background(), "cer-1", "s1", "alice", "approved", "", "", "")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.CeremonyID != "cer-1" {
		t.Fatalf("got CeremonyID=%q, want %q", result.CeremonyID, "cer-1")
	}
	if planID != "plan-43" {
		t.Fatalf("got planID=%q, want %q", planID, "plan-43")
	}
}

func TestApproveReviewPlan_RPCError(t *testing.T) {
	fake := &fakePlanningServer{
		approveReviewPlanErr: status.Error(codes.FailedPrecondition, "not in reviewing state"),
	}
	c := setupBufconn(t, fake)

	_, _, err := c.ApproveReviewPlan(context.Background(), "c", "s", "u", "n", "", "", "")
	if err == nil {
		t.Fatal("expected error, got nil")
	}
}

// ---------------------------------------------------------------------------
// RejectReviewPlan
// ---------------------------------------------------------------------------

func TestRejectReviewPlan_Success(t *testing.T) {
	fake := &fakePlanningServer{
		rejectReviewPlanResp: &pb.RejectReviewPlanResponse{
			Ceremony: &pb.BacklogReviewCeremony{
				CeremonyId: "cer-1",
				Status:     "REVIEWING",
			},
		},
	}
	c := setupBufconn(t, fake)

	result, err := c.RejectReviewPlan(context.Background(), "cer-1", "s1", "bob", "scope too large")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.CeremonyID != "cer-1" {
		t.Fatalf("got CeremonyID=%q, want %q", result.CeremonyID, "cer-1")
	}
}

func TestRejectReviewPlan_RPCError(t *testing.T) {
	fake := &fakePlanningServer{
		rejectReviewPlanErr: status.Error(codes.InvalidArgument, "empty reason"),
	}
	c := setupBufconn(t, fake)

	_, err := c.RejectReviewPlan(context.Background(), "c", "s", "u", "")
	if err == nil {
		t.Fatal("expected error, got nil")
	}
}

// ---------------------------------------------------------------------------
// CompleteBacklogReview
// ---------------------------------------------------------------------------

func TestCompleteBacklogReview_Success(t *testing.T) {
	completedAt := "2025-03-05T18:00:00Z"
	fake := &fakePlanningServer{
		completeBacklogReviewResp: &pb.CompleteBacklogReviewCeremonyResponse{
			Ceremony: &pb.BacklogReviewCeremony{
				CeremonyId:  "cer-1",
				Status:      "COMPLETED",
				CompletedAt: &completedAt,
			},
		},
	}
	c := setupBufconn(t, fake)

	result, err := c.CompleteBacklogReview(context.Background(), "cer-1", "alice")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.CeremonyID != "cer-1" {
		t.Fatalf("got CeremonyID=%q, want %q", result.CeremonyID, "cer-1")
	}
	if result.Status != "COMPLETED" {
		t.Fatalf("got Status=%q, want %q", result.Status, "COMPLETED")
	}
	if result.CompletedAt != completedAt {
		t.Fatalf("got CompletedAt=%q, want %q", result.CompletedAt, completedAt)
	}
}

func TestCompleteBacklogReview_RPCError(t *testing.T) {
	fake := &fakePlanningServer{
		completeBacklogReviewErr: status.Error(codes.FailedPrecondition, "not all reviewed"),
	}
	c := setupBufconn(t, fake)

	_, err := c.CompleteBacklogReview(context.Background(), "cer-1", "alice")
	if err == nil {
		t.Fatal("expected error, got nil")
	}
}

// ---------------------------------------------------------------------------
// CancelBacklogReview
// ---------------------------------------------------------------------------

func TestCancelBacklogReview_Success(t *testing.T) {
	fake := &fakePlanningServer{
		cancelBacklogReviewResp: &pb.CancelBacklogReviewCeremonyResponse{
			Ceremony: &pb.BacklogReviewCeremony{
				CeremonyId: "cer-1",
				Status:     "CANCELLED",
			},
		},
	}
	c := setupBufconn(t, fake)

	result, err := c.CancelBacklogReview(context.Background(), "cer-1", "bob")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.CeremonyID != "cer-1" {
		t.Fatalf("got CeremonyID=%q, want %q", result.CeremonyID, "cer-1")
	}
	if result.Status != "CANCELLED" {
		t.Fatalf("got Status=%q, want %q", result.Status, "CANCELLED")
	}
}

func TestCancelBacklogReview_RPCError(t *testing.T) {
	fake := &fakePlanningServer{
		cancelBacklogReviewErr: status.Error(codes.FailedPrecondition, "already completed"),
	}
	c := setupBufconn(t, fake)

	_, err := c.CancelBacklogReview(context.Background(), "cer-1", "bob")
	if err == nil {
		t.Fatal("expected error, got nil")
	}
}

// ---------------------------------------------------------------------------
// Close
// ---------------------------------------------------------------------------

func TestClose(t *testing.T) {
	fake := &fakePlanningServer{}
	c := setupBufconn(t, fake)

	err := c.Close()
	if err != nil {
		t.Fatalf("unexpected error closing client: %v", err)
	}
}

// ---------------------------------------------------------------------------
// backlogReviewToResult with nil ceremony
// ---------------------------------------------------------------------------

func TestBacklogReviewToResult_NilCeremony(t *testing.T) {
	result := backlogReviewToResult(nil)
	if result.CeremonyID != "" {
		t.Fatalf("expected empty CeremonyID for nil ceremony, got %q", result.CeremonyID)
	}
}

// ---------------------------------------------------------------------------
// storyReviewToItem with nil review result
// ---------------------------------------------------------------------------

func TestStoryReviewToItem_NilResult(t *testing.T) {
	item := storyReviewToItem(nil)
	if item.StoryID != "" {
		t.Fatalf("expected empty StoryID for nil review, got %q", item.StoryID)
	}
}

// ---------------------------------------------------------------------------
// planPreliminaryToResult with nil plan
// ---------------------------------------------------------------------------

func TestPlanPreliminaryToResult_NilPlan(t *testing.T) {
	result := planPreliminaryToResult(nil)
	if result.Title != "" {
		t.Fatalf("expected empty Title for nil plan, got %q", result.Title)
	}
}

// ---------------------------------------------------------------------------
// storyReviewToItem with optional pointer fields populated
// ---------------------------------------------------------------------------

func TestStoryReviewToItem_AllFieldsPopulated(t *testing.T) {
	approvedBy := "alice"
	approvedAt := "2025-03-01T12:00:00Z"
	rejectedBy := "bob"
	rejectedAt := "2025-03-02T12:00:00Z"
	rejectionReason := "too complex"
	poNotes := "looks good"
	poConcerns := "performance"
	priorityAdj := "HIGH"
	poPrioReason := "critical path"
	planID := "plan-99"

	item := storyReviewToItem(&pb.StoryReviewResult{
		StoryId:            "s1",
		ArchitectFeedback:  "great",
		QaFeedback:         "needs tests",
		DevopsFeedback:     "ok",
		ApprovalStatus:     "APPROVED",
		ReviewedAt:         "2025-03-01",
		ApprovedBy:         &approvedBy,
		ApprovedAt:         &approvedAt,
		RejectedBy:         &rejectedBy,
		RejectedAt:         &rejectedAt,
		RejectionReason:    &rejectionReason,
		PoNotes:            &poNotes,
		PoConcerns:         &poConcerns,
		PriorityAdjustment: &priorityAdj,
		PoPriorityReason:   &poPrioReason,
		PlanId:             &planID,
		Recommendations:    []string{"add monitoring"},
		PlanPreliminary: &pb.PlanPreliminary{
			Title:               "Plan",
			Description:         "desc",
			TechnicalNotes:      "notes",
			EstimatedComplexity: "HIGH",
			AcceptanceCriteria:  []string{"ac1", "ac2"},
			Roles:               []string{"dev", "qa"},
			Dependencies:        []string{"dep1"},
			TasksOutline:        []string{"task1", "task2"},
		},
	})

	checks := []struct {
		name string
		got  string
		want string
	}{
		{"StoryID", item.StoryID, "s1"},
		{"ArchitectFeedback", item.ArchitectFeedback, "great"},
		{"QAFeedback", item.QAFeedback, "needs tests"},
		{"DevopsFeedback", item.DevopsFeedback, "ok"},
		{"ApprovalStatus", item.ApprovalStatus, "APPROVED"},
		{"ReviewedAt", item.ReviewedAt, "2025-03-01"},
		{"ApprovedBy", item.ApprovedBy, "alice"},
		{"ApprovedAt", item.ApprovedAt, "2025-03-01T12:00:00Z"},
		{"RejectedBy", item.RejectedBy, "bob"},
		{"RejectedAt", item.RejectedAt, "2025-03-02T12:00:00Z"},
		{"RejectionReason", item.RejectionReason, "too complex"},
		{"PONotes", item.PONotes, "looks good"},
		{"POConcerns", item.POConcerns, "performance"},
		{"PriorityAdjustment", item.PriorityAdjustment, "HIGH"},
		{"POPriorityReason", item.POPriorityReason, "critical path"},
		{"PlanID", item.PlanID, "plan-99"},
	}
	for _, tc := range checks {
		if tc.got != tc.want {
			t.Errorf("%s: got %q, want %q", tc.name, tc.got, tc.want)
		}
	}

	// Check plan preliminary
	if item.PlanPreliminary.Title != "Plan" {
		t.Errorf("PlanPreliminary.Title: got %q, want %q", item.PlanPreliminary.Title, "Plan")
	}
	if len(item.PlanPreliminary.AcceptanceCriteria) != 2 {
		t.Errorf("PlanPreliminary.AcceptanceCriteria length: got %d, want 2", len(item.PlanPreliminary.AcceptanceCriteria))
	}
	if len(item.PlanPreliminary.Roles) != 2 {
		t.Errorf("PlanPreliminary.Roles length: got %d, want 2", len(item.PlanPreliminary.Roles))
	}
	if len(item.PlanPreliminary.Dependencies) != 1 {
		t.Errorf("PlanPreliminary.Dependencies length: got %d, want 1", len(item.PlanPreliminary.Dependencies))
	}
	if len(item.PlanPreliminary.TasksOutline) != 2 {
		t.Errorf("PlanPreliminary.TasksOutline length: got %d, want 2", len(item.PlanPreliminary.TasksOutline))
	}

	if len(item.Recommendations) != 1 || item.Recommendations[0] != "add monitoring" {
		t.Errorf("Recommendations: got %v, want [add monitoring]", item.Recommendations)
	}
}

// ---------------------------------------------------------------------------
// backlogReviewToResult with review results and all optional fields
// ---------------------------------------------------------------------------

func TestBacklogReviewToResult_WithReviewResults(t *testing.T) {
	startedAt := "2025-03-01T10:00:00Z"
	completedAt := "2025-03-05T18:00:00Z"

	result := backlogReviewToResult(&pb.BacklogReviewCeremony{
		CeremonyId:  "cer-1",
		Status:      "COMPLETED",
		CreatedBy:   "alice",
		CreatedAt:   "2025-03-01",
		UpdatedAt:   "2025-03-05",
		StartedAt:   &startedAt,
		CompletedAt: &completedAt,
		StoryIds:    []string{"s1", "s2"},
		ReviewResults: []*pb.StoryReviewResult{
			{StoryId: "s1", ApprovalStatus: "APPROVED"},
			{StoryId: "s2", ApprovalStatus: "REJECTED"},
		},
	})

	if result.CeremonyID != "cer-1" {
		t.Errorf("CeremonyID: got %q, want %q", result.CeremonyID, "cer-1")
	}
	if result.StartedAt != startedAt {
		t.Errorf("StartedAt: got %q, want %q", result.StartedAt, startedAt)
	}
	if result.CompletedAt != completedAt {
		t.Errorf("CompletedAt: got %q, want %q", result.CompletedAt, completedAt)
	}
	if len(result.ReviewResults) != 2 {
		t.Fatalf("ReviewResults length: got %d, want 2", len(result.ReviewResults))
	}
	if result.ReviewResults[0].StoryID != "s1" {
		t.Errorf("ReviewResults[0].StoryID: got %q, want %q", result.ReviewResults[0].StoryID, "s1")
	}
	if result.ReviewResults[1].ApprovalStatus != "REJECTED" {
		t.Errorf("ReviewResults[1].ApprovalStatus: got %q, want %q", result.ReviewResults[1].ApprovalStatus, "REJECTED")
	}
}

// ---------------------------------------------------------------------------
// NewClient — verify it returns error for clearly invalid addr (sanity)
// We cannot test the happy path without a real listener, but we verify the
// returned client is non-nil when dialing a valid-looking address.
// ---------------------------------------------------------------------------

func TestNewClient_CreatesClient(t *testing.T) {
	// grpc.NewClient with insecure transport does lazy connecting, so it
	// won't error for an address that doesn't exist yet.
	c, err := NewClient("localhost:0")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if c == nil {
		t.Fatal("expected non-nil client")
	}
	_ = c.Close()
}

// ---------------------------------------------------------------------------
// Verify error wrapping — errors from RPC should contain method name
// ---------------------------------------------------------------------------

func TestErrorWrapping(t *testing.T) {
	fake := &fakePlanningServer{
		createProjectErr:         status.Error(codes.Internal, "server err"),
		createEpicErr:            status.Error(codes.Internal, "server err"),
		createStoryErr:           status.Error(codes.Internal, "server err"),
		transitionStoryErr:       status.Error(codes.Internal, "server err"),
		createTaskErr:            status.Error(codes.Internal, "server err"),
		approveDecisionErr:       status.Error(codes.Internal, "server err"),
		rejectDecisionErr:        status.Error(codes.Internal, "server err"),
		listProjectsErr:          status.Error(codes.Internal, "server err"),
		listEpicsErr:             status.Error(codes.Internal, "server err"),
		listStoriesErr:           status.Error(codes.Internal, "server err"),
		listTasksErr:             status.Error(codes.Internal, "server err"),
		createBacklogReviewErr:   status.Error(codes.Internal, "server err"),
		startBacklogReviewErr:    status.Error(codes.Internal, "server err"),
		getBacklogReviewErr:      status.Error(codes.Internal, "server err"),
		listBacklogReviewsErr:    status.Error(codes.Internal, "server err"),
		approveReviewPlanErr:     status.Error(codes.Internal, "server err"),
		rejectReviewPlanErr:      status.Error(codes.Internal, "server err"),
		completeBacklogReviewErr: status.Error(codes.Internal, "server err"),
		cancelBacklogReviewErr:   status.Error(codes.Internal, "server err"),
	}
	c := setupBufconn(t, fake)
	ctx := context.Background()

	cases := []struct {
		name    string
		call    func() error
		wantSub string
	}{
		{"CreateProject", func() error { _, e := c.CreateProject(ctx, "n", "d", "u"); return e }, "CreateProject RPC"},
		{"CreateEpic", func() error { _, e := c.CreateEpic(ctx, "p", "t", "d"); return e }, "CreateEpic RPC"},
		{"CreateStory", func() error { _, e := c.CreateStory(ctx, "e", "t", "b", "u"); return e }, "CreateStory RPC"},
		{"TransitionStory", func() error { return c.TransitionStory(ctx, "s", "t") }, "TransitionStory RPC"},
		{"CreateTask", func() error { _, e := c.CreateTask(ctx, "r", "s", "t", "d", "tp", "a", 1, 1); return e }, "CreateTask RPC"},
		{"ApproveDecision", func() error { return c.ApproveDecision(ctx, "s", "d", "u", "c") }, "ApproveDecision RPC"},
		{"RejectDecision", func() error { return c.RejectDecision(ctx, "s", "d", "u", "r") }, "RejectDecision RPC"},
		{"ListProjects", func() error { _, _, e := c.ListProjects(ctx, "", 1, 0); return e }, "ListProjects RPC"},
		{"ListEpics", func() error { _, _, e := c.ListEpics(ctx, "p", "", 1, 0); return e }, "ListEpics RPC"},
		{"ListStories", func() error { _, _, e := c.ListStories(ctx, "e", "", 1, 0); return e }, "ListStories RPC"},
		{"ListTasks", func() error { _, _, e := c.ListTasks(ctx, "s", "", 1, 0); return e }, "ListTasks RPC"},
		{"CreateBacklogReview", func() error { _, e := c.CreateBacklogReview(ctx, "u", nil); return e }, "CreateBacklogReviewCeremony RPC"},
		{"StartBacklogReview", func() error { _, _, e := c.StartBacklogReview(ctx, "c", "u"); return e }, "StartBacklogReviewCeremony RPC"},
		{"GetBacklogReview", func() error { _, e := c.GetBacklogReview(ctx, "c"); return e }, "GetBacklogReviewCeremony RPC"},
		{"ListBacklogReviews", func() error { _, _, e := c.ListBacklogReviews(ctx, "", 1, 0); return e }, "ListBacklogReviewCeremonies RPC"},
		{"ApproveReviewPlan", func() error { _, _, e := c.ApproveReviewPlan(ctx, "c", "s", "u", "n", "", "", ""); return e }, "ApproveReviewPlan RPC"},
		{"RejectReviewPlan", func() error { _, e := c.RejectReviewPlan(ctx, "c", "s", "u", "r"); return e }, "RejectReviewPlan RPC"},
		{"CompleteBacklogReview", func() error { _, e := c.CompleteBacklogReview(ctx, "c", "u"); return e }, "CompleteBacklogReviewCeremony RPC"},
		{"CancelBacklogReview", func() error { _, e := c.CancelBacklogReview(ctx, "c", "u"); return e }, "CancelBacklogReviewCeremony RPC"},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			err := tc.call()
			if err == nil {
				t.Fatal("expected error, got nil")
			}
			got := fmt.Sprintf("%v", err)
			if len(got) == 0 {
				t.Fatal("error message is empty")
			}
			// Verify the error message contains the RPC method name for context.
			if !contains(got, tc.wantSub) {
				t.Errorf("error %q does not contain %q", got, tc.wantSub)
			}
		})
	}
}

func contains(s, sub string) bool {
	return len(s) >= len(sub) && searchString(s, sub)
}

func searchString(s, sub string) bool {
	for i := 0; i <= len(s)-len(sub); i++ {
		if s[i:i+len(sub)] == sub {
			return true
		}
	}
	return false
}
