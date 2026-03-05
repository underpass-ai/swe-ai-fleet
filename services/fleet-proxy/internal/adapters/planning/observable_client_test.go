package planning

import (
	"context"
	"encoding/json"
	"errors"
	"sync"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/event"
)

// ---------------------------------------------------------------------------
// Fake PlanningClient for observable tests — returns configurable responses.
// ---------------------------------------------------------------------------

type stubPlanningClient struct {
	mu sync.Mutex

	// Track calls to verify delegation
	calls []string

	// CreateProject
	createProjectID  string
	createProjectErr error

	// CreateEpic
	createEpicID  string
	createEpicErr error

	// CreateStory
	createStoryID  string
	createStoryErr error

	// TransitionStory
	transitionStoryErr error

	// CreateTask
	createTaskID  string
	createTaskErr error

	// ApproveDecision
	approveDecisionErr error

	// RejectDecision
	rejectDecisionErr error

	// ListProjects
	listProjects      []ports.ProjectResult
	listProjectsTotal int32
	listProjectsErr   error

	// ListEpics
	listEpics      []ports.EpicResult
	listEpicsTotal int32
	listEpicsErr   error

	// ListStories
	listStories      []ports.StoryResult
	listStoriesTotal int32
	listStoriesErr   error

	// ListTasks
	listTasks      []ports.TaskResult
	listTasksTotal int32
	listTasksErr   error

	// CreateBacklogReview
	createBacklogReviewResult ports.BacklogReviewResult
	createBacklogReviewErr    error

	// StartBacklogReview
	startBacklogReviewResult ports.BacklogReviewResult
	startBacklogReviewCount  int32
	startBacklogReviewErr    error

	// GetBacklogReview
	getBacklogReviewResult ports.BacklogReviewResult
	getBacklogReviewErr    error

	// ListBacklogReviews
	listBacklogReviewsResults []ports.BacklogReviewResult
	listBacklogReviewsTotal   int32
	listBacklogReviewsErr     error

	// ApproveReviewPlan
	approveReviewPlanResult ports.BacklogReviewResult
	approveReviewPlanID     string
	approveReviewPlanErr    error

	// RejectReviewPlan
	rejectReviewPlanResult ports.BacklogReviewResult
	rejectReviewPlanErr    error

	// CompleteBacklogReview
	completeBacklogReviewResult ports.BacklogReviewResult
	completeBacklogReviewErr    error

	// CancelBacklogReview
	cancelBacklogReviewResult ports.BacklogReviewResult
	cancelBacklogReviewErr    error
}

func (s *stubPlanningClient) record(method string) {
	s.mu.Lock()
	s.calls = append(s.calls, method)
	s.mu.Unlock()
}

func (s *stubPlanningClient) CreateProject(_ context.Context, _, _, _ string) (string, error) {
	s.record("CreateProject")
	return s.createProjectID, s.createProjectErr
}

func (s *stubPlanningClient) CreateEpic(_ context.Context, _, _, _ string) (string, error) {
	s.record("CreateEpic")
	return s.createEpicID, s.createEpicErr
}

func (s *stubPlanningClient) CreateStory(_ context.Context, _, _, _, _ string) (string, error) {
	s.record("CreateStory")
	return s.createStoryID, s.createStoryErr
}

func (s *stubPlanningClient) TransitionStory(_ context.Context, _, _ string) error {
	s.record("TransitionStory")
	return s.transitionStoryErr
}

func (s *stubPlanningClient) CreateTask(_ context.Context, _, _, _, _, _, _ string, _, _ int32) (string, error) {
	s.record("CreateTask")
	return s.createTaskID, s.createTaskErr
}

func (s *stubPlanningClient) ApproveDecision(_ context.Context, _, _, _, _ string) error {
	s.record("ApproveDecision")
	return s.approveDecisionErr
}

func (s *stubPlanningClient) RejectDecision(_ context.Context, _, _, _, _ string) error {
	s.record("RejectDecision")
	return s.rejectDecisionErr
}

func (s *stubPlanningClient) ListProjects(_ context.Context, _ string, _, _ int32) ([]ports.ProjectResult, int32, error) {
	s.record("ListProjects")
	return s.listProjects, s.listProjectsTotal, s.listProjectsErr
}

func (s *stubPlanningClient) ListEpics(_ context.Context, _, _ string, _, _ int32) ([]ports.EpicResult, int32, error) {
	s.record("ListEpics")
	return s.listEpics, s.listEpicsTotal, s.listEpicsErr
}

func (s *stubPlanningClient) ListStories(_ context.Context, _, _ string, _, _ int32) ([]ports.StoryResult, int32, error) {
	s.record("ListStories")
	return s.listStories, s.listStoriesTotal, s.listStoriesErr
}

func (s *stubPlanningClient) ListTasks(_ context.Context, _, _ string, _, _ int32) ([]ports.TaskResult, int32, error) {
	s.record("ListTasks")
	return s.listTasks, s.listTasksTotal, s.listTasksErr
}

func (s *stubPlanningClient) CreateBacklogReview(_ context.Context, _ string, _ []string) (ports.BacklogReviewResult, error) {
	s.record("CreateBacklogReview")
	return s.createBacklogReviewResult, s.createBacklogReviewErr
}

func (s *stubPlanningClient) StartBacklogReview(_ context.Context, _, _ string) (ports.BacklogReviewResult, int32, error) {
	s.record("StartBacklogReview")
	return s.startBacklogReviewResult, s.startBacklogReviewCount, s.startBacklogReviewErr
}

func (s *stubPlanningClient) GetBacklogReview(_ context.Context, _ string) (ports.BacklogReviewResult, error) {
	s.record("GetBacklogReview")
	return s.getBacklogReviewResult, s.getBacklogReviewErr
}

func (s *stubPlanningClient) ListBacklogReviews(_ context.Context, _ string, _, _ int32) ([]ports.BacklogReviewResult, int32, error) {
	s.record("ListBacklogReviews")
	return s.listBacklogReviewsResults, s.listBacklogReviewsTotal, s.listBacklogReviewsErr
}

func (s *stubPlanningClient) ApproveReviewPlan(_ context.Context, _, _, _, _, _, _, _ string) (ports.BacklogReviewResult, string, error) {
	s.record("ApproveReviewPlan")
	return s.approveReviewPlanResult, s.approveReviewPlanID, s.approveReviewPlanErr
}

func (s *stubPlanningClient) RejectReviewPlan(_ context.Context, _, _, _, _ string) (ports.BacklogReviewResult, error) {
	s.record("RejectReviewPlan")
	return s.rejectReviewPlanResult, s.rejectReviewPlanErr
}

func (s *stubPlanningClient) CompleteBacklogReview(_ context.Context, _, _ string) (ports.BacklogReviewResult, error) {
	s.record("CompleteBacklogReview")
	return s.completeBacklogReviewResult, s.completeBacklogReviewErr
}

func (s *stubPlanningClient) CancelBacklogReview(_ context.Context, _, _ string) (ports.BacklogReviewResult, error) {
	s.record("CancelBacklogReview")
	return s.cancelBacklogReviewResult, s.cancelBacklogReviewErr
}

// ---------------------------------------------------------------------------
// Collecting EventPublisher — records all published events.
// ---------------------------------------------------------------------------

type collectingPublisher struct {
	mu     sync.Mutex
	events []event.FleetEvent
}

func (p *collectingPublisher) Publish(evt event.FleetEvent) {
	p.mu.Lock()
	p.events = append(p.events, evt)
	p.mu.Unlock()
}

func (p *collectingPublisher) lastEvent() (event.FleetEvent, bool) {
	p.mu.Lock()
	defer p.mu.Unlock()
	if len(p.events) == 0 {
		return event.FleetEvent{}, false
	}
	return p.events[len(p.events)-1], true
}

func (p *collectingPublisher) count() int {
	p.mu.Lock()
	defer p.mu.Unlock()
	return len(p.events)
}

// rpcPayload is the JSON structure published by ObservableClient.
type rpcPayload struct {
	Method     string          `json:"method"`
	Success    bool            `json:"success"`
	Error      string          `json:"error,omitempty"`
	DurationMs int64           `json:"duration_ms"`
	Request    json.RawMessage `json:"request,omitempty"`
	Response   json.RawMessage `json:"response,omitempty"`
}

func parsePayload(t *testing.T, data []byte) rpcPayload {
	t.Helper()
	var p rpcPayload
	if err := json.Unmarshal(data, &p); err != nil {
		t.Fatalf("failed to parse event payload: %v", err)
	}
	return p
}

// ---------------------------------------------------------------------------
// NewObservableClient
// ---------------------------------------------------------------------------

func TestNewObservableClient(t *testing.T) {
	inner := &stubPlanningClient{}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)
	if oc == nil {
		t.Fatal("expected non-nil ObservableClient")
	}
	if oc.inner != inner {
		t.Fatal("inner client not wired")
	}
	if oc.publisher != pub {
		t.Fatal("publisher not wired")
	}
}

// ---------------------------------------------------------------------------
// CreateProject — delegates + emits event
// ---------------------------------------------------------------------------

func TestObservable_CreateProject_Success(t *testing.T) {
	inner := &stubPlanningClient{createProjectID: "proj-1"}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	id, err := oc.CreateProject(context.Background(), "My Project", "desc", "alice")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if id != "proj-1" {
		t.Fatalf("got id=%q, want %q", id, "proj-1")
	}
	if len(inner.calls) != 1 || inner.calls[0] != "CreateProject" {
		t.Fatalf("expected inner.CreateProject to be called, got %v", inner.calls)
	}
	if pub.count() != 1 {
		t.Fatalf("expected 1 event, got %d", pub.count())
	}

	evt, _ := pub.lastEvent()
	if evt.Type != event.EventRPCOutbound {
		t.Fatalf("got event type %q, want %q", evt.Type, event.EventRPCOutbound)
	}
	if evt.Producer != "fleet-proxy" {
		t.Fatalf("got producer=%q, want %q", evt.Producer, "fleet-proxy")
	}
	if evt.CorrelationID != "CreateProject" {
		t.Fatalf("got correlationID=%q, want %q", evt.CorrelationID, "CreateProject")
	}

	p := parsePayload(t, evt.Payload)
	if p.Method != "CreateProject" {
		t.Fatalf("payload method=%q, want %q", p.Method, "CreateProject")
	}
	if !p.Success {
		t.Fatal("expected success=true")
	}
	if p.DurationMs < 0 {
		t.Fatalf("unexpected negative duration: %d", p.DurationMs)
	}
}

func TestObservable_CreateProject_Error(t *testing.T) {
	inner := &stubPlanningClient{createProjectErr: errors.New("db fail")}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	_, err := oc.CreateProject(context.Background(), "P", "d", "u")
	if err == nil {
		t.Fatal("expected error, got nil")
	}

	evt, _ := pub.lastEvent()
	p := parsePayload(t, evt.Payload)
	if p.Success {
		t.Fatal("expected success=false on error")
	}
	if p.Error == "" {
		t.Fatal("expected non-empty error in payload")
	}
}

// ---------------------------------------------------------------------------
// CreateEpic
// ---------------------------------------------------------------------------

func TestObservable_CreateEpic_Success(t *testing.T) {
	inner := &stubPlanningClient{createEpicID: "epic-1"}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	id, err := oc.CreateEpic(context.Background(), "proj-1", "Epic Title", "desc")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if id != "epic-1" {
		t.Fatalf("got id=%q, want %q", id, "epic-1")
	}

	evt, _ := pub.lastEvent()
	p := parsePayload(t, evt.Payload)
	if p.Method != "CreateEpic" {
		t.Fatalf("payload method=%q, want %q", p.Method, "CreateEpic")
	}
	if !p.Success {
		t.Fatal("expected success=true")
	}
}

func TestObservable_CreateEpic_Error(t *testing.T) {
	inner := &stubPlanningClient{createEpicErr: errors.New("fail")}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	_, err := oc.CreateEpic(context.Background(), "p", "t", "d")
	if err == nil {
		t.Fatal("expected error")
	}
	p := parsePayload(t, pub.events[0].Payload)
	if p.Success {
		t.Fatal("expected success=false")
	}
}

// ---------------------------------------------------------------------------
// CreateStory
// ---------------------------------------------------------------------------

func TestObservable_CreateStory_Success(t *testing.T) {
	inner := &stubPlanningClient{createStoryID: "story-1"}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	id, err := oc.CreateStory(context.Background(), "epic-1", "Story", "brief", "alice")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if id != "story-1" {
		t.Fatalf("got id=%q, want %q", id, "story-1")
	}

	p := parsePayload(t, pub.events[0].Payload)
	if p.Method != "CreateStory" {
		t.Fatalf("payload method=%q, want %q", p.Method, "CreateStory")
	}
}

// ---------------------------------------------------------------------------
// TransitionStory
// ---------------------------------------------------------------------------

func TestObservable_TransitionStory_Success(t *testing.T) {
	inner := &stubPlanningClient{}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	err := oc.TransitionStory(context.Background(), "story-1", "IN_PROGRESS")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	p := parsePayload(t, pub.events[0].Payload)
	if p.Method != "TransitionStory" {
		t.Fatalf("payload method=%q, want %q", p.Method, "TransitionStory")
	}
	if !p.Success {
		t.Fatal("expected success=true")
	}
}

func TestObservable_TransitionStory_Error(t *testing.T) {
	inner := &stubPlanningClient{transitionStoryErr: errors.New("bad transition")}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	err := oc.TransitionStory(context.Background(), "s", "X")
	if err == nil {
		t.Fatal("expected error")
	}

	p := parsePayload(t, pub.events[0].Payload)
	if p.Success {
		t.Fatal("expected success=false")
	}
}

// ---------------------------------------------------------------------------
// CreateTask
// ---------------------------------------------------------------------------

func TestObservable_CreateTask_Success(t *testing.T) {
	inner := &stubPlanningClient{createTaskID: "task-1"}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	id, err := oc.CreateTask(context.Background(), "req-1", "story-1", "Task", "desc", "dev", "agent", 4, 1)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if id != "task-1" {
		t.Fatalf("got id=%q, want %q", id, "task-1")
	}

	p := parsePayload(t, pub.events[0].Payload)
	if p.Method != "CreateTask" {
		t.Fatalf("payload method=%q, want %q", p.Method, "CreateTask")
	}
}

func TestObservable_CreateTask_Error(t *testing.T) {
	inner := &stubPlanningClient{createTaskErr: errors.New("fail")}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	_, err := oc.CreateTask(context.Background(), "r", "s", "t", "d", "tp", "a", 1, 1)
	if err == nil {
		t.Fatal("expected error")
	}
	p := parsePayload(t, pub.events[0].Payload)
	if p.Success {
		t.Fatal("expected success=false")
	}
}

// ---------------------------------------------------------------------------
// ApproveDecision
// ---------------------------------------------------------------------------

func TestObservable_ApproveDecision_Success(t *testing.T) {
	inner := &stubPlanningClient{}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	err := oc.ApproveDecision(context.Background(), "story-1", "dec-1", "alice", "looks good")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	p := parsePayload(t, pub.events[0].Payload)
	if p.Method != "ApproveDecision" {
		t.Fatalf("payload method=%q, want %q", p.Method, "ApproveDecision")
	}
}

func TestObservable_ApproveDecision_Error(t *testing.T) {
	inner := &stubPlanningClient{approveDecisionErr: errors.New("denied")}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	err := oc.ApproveDecision(context.Background(), "s", "d", "u", "c")
	if err == nil {
		t.Fatal("expected error")
	}
	p := parsePayload(t, pub.events[0].Payload)
	if p.Success {
		t.Fatal("expected success=false")
	}
}

// ---------------------------------------------------------------------------
// RejectDecision
// ---------------------------------------------------------------------------

func TestObservable_RejectDecision_Success(t *testing.T) {
	inner := &stubPlanningClient{}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	err := oc.RejectDecision(context.Background(), "story-1", "dec-1", "bob", "needs rework")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	p := parsePayload(t, pub.events[0].Payload)
	if p.Method != "RejectDecision" {
		t.Fatalf("payload method=%q, want %q", p.Method, "RejectDecision")
	}
}

func TestObservable_RejectDecision_Error(t *testing.T) {
	inner := &stubPlanningClient{rejectDecisionErr: errors.New("denied")}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	err := oc.RejectDecision(context.Background(), "s", "d", "u", "r")
	if err == nil {
		t.Fatal("expected error")
	}
	p := parsePayload(t, pub.events[0].Payload)
	if p.Success {
		t.Fatal("expected success=false")
	}
}

// ---------------------------------------------------------------------------
// ListProjects
// ---------------------------------------------------------------------------

func TestObservable_ListProjects_Success(t *testing.T) {
	inner := &stubPlanningClient{
		listProjects:      []ports.ProjectResult{{ProjectID: "p1"}},
		listProjectsTotal: 5,
	}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	projects, total, err := oc.ListProjects(context.Background(), "active", 10, 0)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if total != 5 {
		t.Fatalf("got total=%d, want 5", total)
	}
	if len(projects) != 1 {
		t.Fatalf("got %d projects, want 1", len(projects))
	}

	p := parsePayload(t, pub.events[0].Payload)
	if p.Method != "ListProjects" {
		t.Fatalf("payload method=%q, want %q", p.Method, "ListProjects")
	}
	if !p.Success {
		t.Fatal("expected success=true")
	}
}

func TestObservable_ListProjects_Error(t *testing.T) {
	inner := &stubPlanningClient{listProjectsErr: errors.New("fail")}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	_, _, err := oc.ListProjects(context.Background(), "", 10, 0)
	if err == nil {
		t.Fatal("expected error")
	}
	p := parsePayload(t, pub.events[0].Payload)
	if p.Success {
		t.Fatal("expected success=false")
	}
}

// ---------------------------------------------------------------------------
// ListEpics
// ---------------------------------------------------------------------------

func TestObservable_ListEpics_Success(t *testing.T) {
	inner := &stubPlanningClient{
		listEpics:      []ports.EpicResult{{EpicID: "e1"}},
		listEpicsTotal: 3,
	}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	epics, total, err := oc.ListEpics(context.Background(), "p1", "active", 10, 0)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if total != 3 {
		t.Fatalf("got total=%d, want 3", total)
	}
	if len(epics) != 1 {
		t.Fatalf("got %d epics, want 1", len(epics))
	}

	p := parsePayload(t, pub.events[0].Payload)
	if p.Method != "ListEpics" {
		t.Fatalf("payload method=%q, want %q", p.Method, "ListEpics")
	}
}

func TestObservable_ListEpics_Error(t *testing.T) {
	inner := &stubPlanningClient{listEpicsErr: errors.New("fail")}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	_, _, err := oc.ListEpics(context.Background(), "p1", "", 10, 0)
	if err == nil {
		t.Fatal("expected error")
	}
}

// ---------------------------------------------------------------------------
// ListStories
// ---------------------------------------------------------------------------

func TestObservable_ListStories_Success(t *testing.T) {
	inner := &stubPlanningClient{
		listStories:      []ports.StoryResult{{StoryID: "s1", DorScore: 80}},
		listStoriesTotal: 7,
	}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	stories, total, err := oc.ListStories(context.Background(), "e1", "DRAFT", 10, 0)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if total != 7 {
		t.Fatalf("got total=%d, want 7", total)
	}
	if len(stories) != 1 {
		t.Fatalf("got %d stories, want 1", len(stories))
	}

	p := parsePayload(t, pub.events[0].Payload)
	if p.Method != "ListStories" {
		t.Fatalf("payload method=%q, want %q", p.Method, "ListStories")
	}
}

func TestObservable_ListStories_Error(t *testing.T) {
	inner := &stubPlanningClient{listStoriesErr: errors.New("fail")}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	_, _, err := oc.ListStories(context.Background(), "e1", "", 10, 0)
	if err == nil {
		t.Fatal("expected error")
	}
}

// ---------------------------------------------------------------------------
// ListTasks
// ---------------------------------------------------------------------------

func TestObservable_ListTasks_Success(t *testing.T) {
	inner := &stubPlanningClient{
		listTasks:      []ports.TaskResult{{TaskID: "t1", Priority: 1}},
		listTasksTotal: 4,
	}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	tasks, total, err := oc.ListTasks(context.Background(), "s1", "todo", 10, 0)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if total != 4 {
		t.Fatalf("got total=%d, want 4", total)
	}
	if len(tasks) != 1 {
		t.Fatalf("got %d tasks, want 1", len(tasks))
	}

	p := parsePayload(t, pub.events[0].Payload)
	if p.Method != "ListTasks" {
		t.Fatalf("payload method=%q, want %q", p.Method, "ListTasks")
	}
}

func TestObservable_ListTasks_Error(t *testing.T) {
	inner := &stubPlanningClient{listTasksErr: errors.New("fail")}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	_, _, err := oc.ListTasks(context.Background(), "s1", "", 10, 0)
	if err == nil {
		t.Fatal("expected error")
	}
}

// ---------------------------------------------------------------------------
// CreateBacklogReview
// ---------------------------------------------------------------------------

func TestObservable_CreateBacklogReview_Success(t *testing.T) {
	inner := &stubPlanningClient{
		createBacklogReviewResult: ports.BacklogReviewResult{
			CeremonyID: "cer-1",
			Status:     "DRAFT",
		},
	}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	result, err := oc.CreateBacklogReview(context.Background(), "alice", []string{"s1", "s2"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.CeremonyID != "cer-1" {
		t.Fatalf("got CeremonyID=%q, want %q", result.CeremonyID, "cer-1")
	}

	p := parsePayload(t, pub.events[0].Payload)
	if p.Method != "CreateBacklogReview" {
		t.Fatalf("payload method=%q, want %q", p.Method, "CreateBacklogReview")
	}
	if !p.Success {
		t.Fatal("expected success=true")
	}
}

func TestObservable_CreateBacklogReview_Error(t *testing.T) {
	inner := &stubPlanningClient{createBacklogReviewErr: errors.New("fail")}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	_, err := oc.CreateBacklogReview(context.Background(), "u", nil)
	if err == nil {
		t.Fatal("expected error")
	}
	p := parsePayload(t, pub.events[0].Payload)
	if p.Success {
		t.Fatal("expected success=false")
	}
}

// ---------------------------------------------------------------------------
// StartBacklogReview
// ---------------------------------------------------------------------------

func TestObservable_StartBacklogReview_Success(t *testing.T) {
	inner := &stubPlanningClient{
		startBacklogReviewResult: ports.BacklogReviewResult{
			CeremonyID: "cer-1",
			Status:     "IN_PROGRESS",
		},
		startBacklogReviewCount: 6,
	}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	result, count, err := oc.StartBacklogReview(context.Background(), "cer-1", "alice")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.Status != "IN_PROGRESS" {
		t.Fatalf("got Status=%q, want %q", result.Status, "IN_PROGRESS")
	}
	if count != 6 {
		t.Fatalf("got count=%d, want 6", count)
	}

	p := parsePayload(t, pub.events[0].Payload)
	if p.Method != "StartBacklogReview" {
		t.Fatalf("payload method=%q, want %q", p.Method, "StartBacklogReview")
	}
}

func TestObservable_StartBacklogReview_Error(t *testing.T) {
	inner := &stubPlanningClient{startBacklogReviewErr: errors.New("fail")}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	_, _, err := oc.StartBacklogReview(context.Background(), "c", "u")
	if err == nil {
		t.Fatal("expected error")
	}
}

// ---------------------------------------------------------------------------
// GetBacklogReview
// ---------------------------------------------------------------------------

func TestObservable_GetBacklogReview_Success(t *testing.T) {
	inner := &stubPlanningClient{
		getBacklogReviewResult: ports.BacklogReviewResult{
			CeremonyID: "cer-1",
			Status:     "REVIEWING",
		},
	}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	result, err := oc.GetBacklogReview(context.Background(), "cer-1")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.CeremonyID != "cer-1" {
		t.Fatalf("got CeremonyID=%q, want %q", result.CeremonyID, "cer-1")
	}

	p := parsePayload(t, pub.events[0].Payload)
	if p.Method != "GetBacklogReview" {
		t.Fatalf("payload method=%q, want %q", p.Method, "GetBacklogReview")
	}
}

func TestObservable_GetBacklogReview_Error(t *testing.T) {
	inner := &stubPlanningClient{getBacklogReviewErr: errors.New("not found")}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	_, err := oc.GetBacklogReview(context.Background(), "cer-x")
	if err == nil {
		t.Fatal("expected error")
	}
}

// ---------------------------------------------------------------------------
// ListBacklogReviews
// ---------------------------------------------------------------------------

func TestObservable_ListBacklogReviews_Success(t *testing.T) {
	inner := &stubPlanningClient{
		listBacklogReviewsResults: []ports.BacklogReviewResult{
			{CeremonyID: "cer-1"},
			{CeremonyID: "cer-2"},
		},
		listBacklogReviewsTotal: 2,
	}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	results, total, err := oc.ListBacklogReviews(context.Background(), "COMPLETED", 10, 0)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if total != 2 {
		t.Fatalf("got total=%d, want 2", total)
	}
	if len(results) != 2 {
		t.Fatalf("got %d results, want 2", len(results))
	}

	p := parsePayload(t, pub.events[0].Payload)
	if p.Method != "ListBacklogReviews" {
		t.Fatalf("payload method=%q, want %q", p.Method, "ListBacklogReviews")
	}
}

func TestObservable_ListBacklogReviews_Error(t *testing.T) {
	inner := &stubPlanningClient{listBacklogReviewsErr: errors.New("fail")}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	_, _, err := oc.ListBacklogReviews(context.Background(), "", 10, 0)
	if err == nil {
		t.Fatal("expected error")
	}
}

// ---------------------------------------------------------------------------
// ApproveReviewPlan
// ---------------------------------------------------------------------------

func TestObservable_ApproveReviewPlan_Success(t *testing.T) {
	inner := &stubPlanningClient{
		approveReviewPlanResult: ports.BacklogReviewResult{CeremonyID: "cer-1"},
		approveReviewPlanID:     "plan-42",
	}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	result, planID, err := oc.ApproveReviewPlan(context.Background(), "cer-1", "s1", "alice", "notes", "concerns", "HIGH", "reason")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.CeremonyID != "cer-1" {
		t.Fatalf("got CeremonyID=%q, want %q", result.CeremonyID, "cer-1")
	}
	if planID != "plan-42" {
		t.Fatalf("got planID=%q, want %q", planID, "plan-42")
	}

	p := parsePayload(t, pub.events[0].Payload)
	if p.Method != "ApproveReviewPlan" {
		t.Fatalf("payload method=%q, want %q", p.Method, "ApproveReviewPlan")
	}
}

func TestObservable_ApproveReviewPlan_Error(t *testing.T) {
	inner := &stubPlanningClient{approveReviewPlanErr: errors.New("fail")}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	_, _, err := oc.ApproveReviewPlan(context.Background(), "c", "s", "u", "n", "", "", "")
	if err == nil {
		t.Fatal("expected error")
	}
}

// ---------------------------------------------------------------------------
// RejectReviewPlan
// ---------------------------------------------------------------------------

func TestObservable_RejectReviewPlan_Success(t *testing.T) {
	inner := &stubPlanningClient{
		rejectReviewPlanResult: ports.BacklogReviewResult{CeremonyID: "cer-1"},
	}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	result, err := oc.RejectReviewPlan(context.Background(), "cer-1", "s1", "bob", "too broad")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.CeremonyID != "cer-1" {
		t.Fatalf("got CeremonyID=%q, want %q", result.CeremonyID, "cer-1")
	}

	p := parsePayload(t, pub.events[0].Payload)
	if p.Method != "RejectReviewPlan" {
		t.Fatalf("payload method=%q, want %q", p.Method, "RejectReviewPlan")
	}
}

func TestObservable_RejectReviewPlan_Error(t *testing.T) {
	inner := &stubPlanningClient{rejectReviewPlanErr: errors.New("fail")}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	_, err := oc.RejectReviewPlan(context.Background(), "c", "s", "u", "r")
	if err == nil {
		t.Fatal("expected error")
	}
}

// ---------------------------------------------------------------------------
// CompleteBacklogReview
// ---------------------------------------------------------------------------

func TestObservable_CompleteBacklogReview_Success(t *testing.T) {
	inner := &stubPlanningClient{
		completeBacklogReviewResult: ports.BacklogReviewResult{
			CeremonyID: "cer-1",
			Status:     "COMPLETED",
		},
	}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	result, err := oc.CompleteBacklogReview(context.Background(), "cer-1", "alice")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.Status != "COMPLETED" {
		t.Fatalf("got Status=%q, want %q", result.Status, "COMPLETED")
	}

	p := parsePayload(t, pub.events[0].Payload)
	if p.Method != "CompleteBacklogReview" {
		t.Fatalf("payload method=%q, want %q", p.Method, "CompleteBacklogReview")
	}
}

func TestObservable_CompleteBacklogReview_Error(t *testing.T) {
	inner := &stubPlanningClient{completeBacklogReviewErr: errors.New("fail")}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	_, err := oc.CompleteBacklogReview(context.Background(), "c", "u")
	if err == nil {
		t.Fatal("expected error")
	}
}

// ---------------------------------------------------------------------------
// CancelBacklogReview
// ---------------------------------------------------------------------------

func TestObservable_CancelBacklogReview_Success(t *testing.T) {
	inner := &stubPlanningClient{
		cancelBacklogReviewResult: ports.BacklogReviewResult{
			CeremonyID: "cer-1",
			Status:     "CANCELLED",
		},
	}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	result, err := oc.CancelBacklogReview(context.Background(), "cer-1", "bob")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.Status != "CANCELLED" {
		t.Fatalf("got Status=%q, want %q", result.Status, "CANCELLED")
	}

	p := parsePayload(t, pub.events[0].Payload)
	if p.Method != "CancelBacklogReview" {
		t.Fatalf("payload method=%q, want %q", p.Method, "CancelBacklogReview")
	}
}

func TestObservable_CancelBacklogReview_Error(t *testing.T) {
	inner := &stubPlanningClient{cancelBacklogReviewErr: errors.New("fail")}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	_, err := oc.CancelBacklogReview(context.Background(), "c", "u")
	if err == nil {
		t.Fatal("expected error")
	}
}

// ---------------------------------------------------------------------------
// marshalAny helper
// ---------------------------------------------------------------------------

func TestMarshalAny_Nil(t *testing.T) {
	result := marshalAny(nil)
	if result != nil {
		t.Fatalf("expected nil for nil input, got %v", result)
	}
}

func TestMarshalAny_ValidJSON(t *testing.T) {
	result := marshalAny(map[string]string{"key": "value"})
	if result == nil {
		t.Fatal("expected non-nil result")
	}
	var m map[string]string
	if err := json.Unmarshal(result, &m); err != nil {
		t.Fatalf("failed to unmarshal: %v", err)
	}
	if m["key"] != "value" {
		t.Fatalf("got key=%q, want %q", m["key"], "value")
	}
}

func TestMarshalAny_UnmarshalableValue(t *testing.T) {
	// Channels cannot be marshalled to JSON.
	result := marshalAny(make(chan int))
	if result != nil {
		t.Fatalf("expected nil for unmarshalable value, got %v", result)
	}
}

// ---------------------------------------------------------------------------
// Event metadata verification — idempotency key and timestamp
// ---------------------------------------------------------------------------

func TestObservable_EventMetadata(t *testing.T) {
	inner := &stubPlanningClient{createProjectID: "proj-1"}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)

	_, _ = oc.CreateProject(context.Background(), "P", "d", "u")
	_, _ = oc.CreateProject(context.Background(), "P", "d", "u")

	if pub.count() != 2 {
		t.Fatalf("expected 2 events, got %d", pub.count())
	}

	// Each event should have a unique idempotency key.
	e1 := pub.events[0]
	e2 := pub.events[1]
	if e1.IdempotencyKey == e2.IdempotencyKey {
		t.Fatalf("idempotency keys should be unique, both are %q", e1.IdempotencyKey)
	}

	// Timestamps should be non-zero.
	if e1.Timestamp.IsZero() {
		t.Fatal("event 1 timestamp is zero")
	}
	if e2.Timestamp.IsZero() {
		t.Fatal("event 2 timestamp is zero")
	}
}

// ---------------------------------------------------------------------------
// Verify all methods emit exactly one event each
// ---------------------------------------------------------------------------

func TestObservable_AllMethods_EmitOneEvent(t *testing.T) {
	inner := &stubPlanningClient{
		createProjectID: "p1",
		createEpicID:    "e1",
		createStoryID:   "s1",
		createTaskID:    "t1",
		listProjects:    []ports.ProjectResult{{ProjectID: "p1"}},
		listEpics:       []ports.EpicResult{{EpicID: "e1"}},
		listStories:     []ports.StoryResult{{StoryID: "s1"}},
		listTasks:       []ports.TaskResult{{TaskID: "t1"}},
		createBacklogReviewResult:   ports.BacklogReviewResult{CeremonyID: "c1"},
		startBacklogReviewResult:    ports.BacklogReviewResult{CeremonyID: "c1"},
		getBacklogReviewResult:      ports.BacklogReviewResult{CeremonyID: "c1"},
		listBacklogReviewsResults:   []ports.BacklogReviewResult{{CeremonyID: "c1"}},
		approveReviewPlanResult:     ports.BacklogReviewResult{CeremonyID: "c1"},
		rejectReviewPlanResult:      ports.BacklogReviewResult{CeremonyID: "c1"},
		completeBacklogReviewResult: ports.BacklogReviewResult{CeremonyID: "c1"},
		cancelBacklogReviewResult:   ports.BacklogReviewResult{CeremonyID: "c1"},
	}
	pub := &collectingPublisher{}
	oc := NewObservableClient(inner, pub)
	ctx := context.Background()

	// Call all 18 methods
	_, _ = oc.CreateProject(ctx, "n", "d", "u")
	_, _ = oc.CreateEpic(ctx, "p", "t", "d")
	_, _ = oc.CreateStory(ctx, "e", "t", "b", "u")
	_ = oc.TransitionStory(ctx, "s", "t")
	_, _ = oc.CreateTask(ctx, "r", "s", "t", "d", "tp", "a", 1, 1)
	_ = oc.ApproveDecision(ctx, "s", "d", "u", "c")
	_ = oc.RejectDecision(ctx, "s", "d", "u", "r")
	_, _, _ = oc.ListProjects(ctx, "", 10, 0)
	_, _, _ = oc.ListEpics(ctx, "p", "", 10, 0)
	_, _, _ = oc.ListStories(ctx, "e", "", 10, 0)
	_, _, _ = oc.ListTasks(ctx, "s", "", 10, 0)
	_, _ = oc.CreateBacklogReview(ctx, "u", []string{"s1"})
	_, _, _ = oc.StartBacklogReview(ctx, "c", "u")
	_, _ = oc.GetBacklogReview(ctx, "c")
	_, _, _ = oc.ListBacklogReviews(ctx, "", 10, 0)
	_, _, _ = oc.ApproveReviewPlan(ctx, "c", "s", "u", "n", "", "", "")
	_, _ = oc.RejectReviewPlan(ctx, "c", "s", "u", "r")
	_, _ = oc.CompleteBacklogReview(ctx, "c", "u")
	_, _ = oc.CancelBacklogReview(ctx, "c", "u")

	expectedCount := 19 // 19 method calls
	if pub.count() != expectedCount {
		t.Fatalf("expected %d events, got %d", expectedCount, pub.count())
	}

	// Verify all events are EventRPCOutbound.
	for i, evt := range pub.events {
		if evt.Type != event.EventRPCOutbound {
			t.Errorf("event[%d] type=%q, want %q", i, evt.Type, event.EventRPCOutbound)
		}
	}

	// Verify inner client received all calls.
	if len(inner.calls) != expectedCount {
		t.Fatalf("expected %d inner calls, got %d: %v", expectedCount, len(inner.calls), inner.calls)
	}

	// Verify expected method names in payloads.
	expectedMethods := []string{
		"CreateProject", "CreateEpic", "CreateStory", "TransitionStory",
		"CreateTask", "ApproveDecision", "RejectDecision",
		"ListProjects", "ListEpics", "ListStories", "ListTasks",
		"CreateBacklogReview", "StartBacklogReview", "GetBacklogReview",
		"ListBacklogReviews", "ApproveReviewPlan", "RejectReviewPlan",
		"CompleteBacklogReview", "CancelBacklogReview",
	}
	for i, wantMethod := range expectedMethods {
		p := parsePayload(t, pub.events[i].Payload)
		if p.Method != wantMethod {
			t.Errorf("event[%d] method=%q, want %q", i, p.Method, wantMethod)
		}
	}
}
