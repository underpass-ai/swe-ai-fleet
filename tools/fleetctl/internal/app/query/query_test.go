package query

import (
	"context"
	"errors"
	"fmt"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// ---------------------------------------------------------------------------
// fakeFleetClient — hand-written fake covering every ports.FleetClient method.
// Only the methods exercised by query handlers carry configurable behaviour;
// the rest return sensible zero values or "not implemented" errors.
// ---------------------------------------------------------------------------

type fakeFleetClient struct {
	// Return values for query methods under test.
	projects     []domain.ProjectSummary
	projectTotal int32
	projectErr   error

	stories    []domain.StorySummary
	storyTotal int32
	storyErr   error

	tasks     []domain.TaskSummary
	taskTotal int32
	taskErr   error

	ceremony    domain.CeremonyStatus
	ceremonyErr error

	epics     []domain.EpicSummary
	epicTotal int32
	epicErr   error

	ceremonies     []domain.CeremonyStatus
	ceremonyTotal  int32
	ceremoniesErr  error

	backlogReview    domain.BacklogReview
	backlogReviewErr error

	backlogReviews      []domain.BacklogReview
	backlogReviewTotal  int32
	backlogReviewsErr   error

	eventsCh  chan domain.FleetEvent
	eventsErr error
}

// --- Methods used by the query handlers under test -------------------------

func (f *fakeFleetClient) ListProjects(_ context.Context, _ string, _, _ int32) ([]domain.ProjectSummary, int32, error) {
	return f.projects, f.projectTotal, f.projectErr
}

func (f *fakeFleetClient) ListStories(_ context.Context, _, _ string, _, _ int32) ([]domain.StorySummary, int32, error) {
	return f.stories, f.storyTotal, f.storyErr
}

func (f *fakeFleetClient) ListTasks(_ context.Context, _, _ string, _, _ int32) ([]domain.TaskSummary, int32, error) {
	return f.tasks, f.taskTotal, f.taskErr
}

func (f *fakeFleetClient) GetCeremony(_ context.Context, _ string) (domain.CeremonyStatus, error) {
	return f.ceremony, f.ceremonyErr
}

func (f *fakeFleetClient) WatchEvents(_ context.Context, _ []string, _ string) (<-chan domain.FleetEvent, error) {
	if f.eventsErr != nil {
		return nil, f.eventsErr
	}
	if f.eventsCh == nil {
		f.eventsCh = make(chan domain.FleetEvent, 4)
	}
	return f.eventsCh, nil
}

// --- Stubs for the rest of the FleetClient interface -----------------------

func (f *fakeFleetClient) Enroll(context.Context, string, string, []byte) ([]byte, []byte, string, string, error) {
	return nil, nil, "", "", fmt.Errorf("not implemented")
}

func (f *fakeFleetClient) Renew(context.Context, []byte) ([]byte, []byte, string, error) {
	return nil, nil, "", fmt.Errorf("not implemented")
}

func (f *fakeFleetClient) CreateProject(context.Context, string, string, string) (domain.ProjectSummary, error) {
	return domain.ProjectSummary{}, fmt.Errorf("not implemented")
}

func (f *fakeFleetClient) CreateEpic(context.Context, string, string, string, string) (domain.EpicSummary, error) {
	return domain.EpicSummary{}, fmt.Errorf("not implemented")
}

func (f *fakeFleetClient) CreateStory(context.Context, string, string, string, string) (domain.StorySummary, error) {
	return domain.StorySummary{}, fmt.Errorf("not implemented")
}

func (f *fakeFleetClient) CreateTask(context.Context, ports.CreateTaskInput) (domain.TaskSummary, error) {
	return domain.TaskSummary{}, fmt.Errorf("not implemented")
}

func (f *fakeFleetClient) TransitionStory(context.Context, string, string) error {
	return fmt.Errorf("not implemented")
}

func (f *fakeFleetClient) StartCeremony(context.Context, string, string, string, string, []string) (domain.CeremonyStatus, error) {
	return domain.CeremonyStatus{}, fmt.Errorf("not implemented")
}

func (f *fakeFleetClient) ListEpics(_ context.Context, _, _ string, _, _ int32) ([]domain.EpicSummary, int32, error) {
	return f.epics, f.epicTotal, f.epicErr
}

func (f *fakeFleetClient) ListCeremonies(_ context.Context, _, _ string, _, _ int32) ([]domain.CeremonyStatus, int32, error) {
	return f.ceremonies, f.ceremonyTotal, f.ceremoniesErr
}

func (f *fakeFleetClient) ApproveDecision(context.Context, string, string, string) error {
	return fmt.Errorf("not implemented")
}

func (f *fakeFleetClient) RejectDecision(context.Context, string, string, string) error {
	return fmt.Errorf("not implemented")
}

func (f *fakeFleetClient) CreateBacklogReview(context.Context, string, []string) (domain.BacklogReview, error) {
	return domain.BacklogReview{}, fmt.Errorf("not implemented")
}

func (f *fakeFleetClient) StartBacklogReview(context.Context, string, string) (domain.BacklogReview, int32, error) {
	return domain.BacklogReview{}, 0, fmt.Errorf("not implemented")
}

func (f *fakeFleetClient) GetBacklogReview(_ context.Context, _ string) (domain.BacklogReview, error) {
	return f.backlogReview, f.backlogReviewErr
}

func (f *fakeFleetClient) ListBacklogReviews(_ context.Context, _ string, _, _ int32) ([]domain.BacklogReview, int32, error) {
	return f.backlogReviews, f.backlogReviewTotal, f.backlogReviewsErr
}

func (f *fakeFleetClient) ApproveReviewPlan(context.Context, ports.ApproveReviewPlanInput) (domain.BacklogReview, string, error) {
	return domain.BacklogReview{}, "", fmt.Errorf("not implemented")
}

func (f *fakeFleetClient) RejectReviewPlan(context.Context, string, string, string, string) (domain.BacklogReview, error) {
	return domain.BacklogReview{}, fmt.Errorf("not implemented")
}

func (f *fakeFleetClient) CompleteBacklogReview(context.Context, string, string) (domain.BacklogReview, error) {
	return domain.BacklogReview{}, fmt.Errorf("not implemented")
}

func (f *fakeFleetClient) CancelBacklogReview(context.Context, string, string) (domain.BacklogReview, error) {
	return domain.BacklogReview{}, fmt.Errorf("not implemented")
}

func (f *fakeFleetClient) Close() error { return nil }

// ---------------------------------------------------------------------------
// ListProjectsHandler tests
// ---------------------------------------------------------------------------

func TestListProjectsHandler_Success(t *testing.T) {
	want := []domain.ProjectSummary{
		{ID: "p-1", Name: "Alpha", Status: "active"},
		{ID: "p-2", Name: "Beta", Status: "archived"},
	}
	fc := &fakeFleetClient{
		projects:     want,
		projectTotal: 2,
	}
	h := NewListProjectsHandler(fc)

	got, total, err := h.Handle(context.Background(), "active", 10, 0)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if total != 2 {
		t.Fatalf("total: got %d, want 2", total)
	}
	if len(got) != len(want) {
		t.Fatalf("projects length: got %d, want %d", len(got), len(want))
	}
	for i := range want {
		if got[i].ID != want[i].ID {
			t.Errorf("project[%d].ID: got %q, want %q", i, got[i].ID, want[i].ID)
		}
		if got[i].Name != want[i].Name {
			t.Errorf("project[%d].Name: got %q, want %q", i, got[i].Name, want[i].Name)
		}
	}
}

func TestListProjectsHandler_EmptyResult(t *testing.T) {
	fc := &fakeFleetClient{
		projects:     nil,
		projectTotal: 0,
	}
	h := NewListProjectsHandler(fc)

	got, total, err := h.Handle(context.Background(), "", 10, 0)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if total != 0 {
		t.Fatalf("total: got %d, want 0", total)
	}
	if len(got) != 0 {
		t.Fatalf("projects length: got %d, want 0", len(got))
	}
}

func TestListProjectsHandler_ClientError(t *testing.T) {
	sentinel := errors.New("connection refused")
	fc := &fakeFleetClient{projectErr: sentinel}
	h := NewListProjectsHandler(fc)

	_, _, err := h.Handle(context.Background(), "", 10, 0)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !errors.Is(err, sentinel) {
		t.Fatalf("error chain should contain sentinel: got %v", err)
	}
	want := "list_projects: connection refused"
	if err.Error() != want {
		t.Fatalf("error message: got %q, want %q", err.Error(), want)
	}
}

// ---------------------------------------------------------------------------
// ListStoriesHandler tests
// ---------------------------------------------------------------------------

func TestListStoriesHandler_Success(t *testing.T) {
	want := []domain.StorySummary{
		{ID: "s-1", EpicID: "e-1", Title: "Implement login", State: "in_progress"},
		{ID: "s-2", EpicID: "e-1", Title: "Add logout", State: "todo"},
	}
	fc := &fakeFleetClient{
		stories:    want,
		storyTotal: 2,
	}
	h := NewListStoriesHandler(fc)

	got, total, err := h.Handle(context.Background(), "e-1", "in_progress", 10, 0)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if total != 2 {
		t.Fatalf("total: got %d, want 2", total)
	}
	if len(got) != len(want) {
		t.Fatalf("stories length: got %d, want %d", len(got), len(want))
	}
	for i := range want {
		if got[i].ID != want[i].ID {
			t.Errorf("story[%d].ID: got %q, want %q", i, got[i].ID, want[i].ID)
		}
		if got[i].Title != want[i].Title {
			t.Errorf("story[%d].Title: got %q, want %q", i, got[i].Title, want[i].Title)
		}
	}
}

func TestListStoriesHandler_EmptyResult(t *testing.T) {
	fc := &fakeFleetClient{
		stories:    nil,
		storyTotal: 0,
	}
	h := NewListStoriesHandler(fc)

	got, total, err := h.Handle(context.Background(), "", "", 10, 0)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if total != 0 {
		t.Fatalf("total: got %d, want 0", total)
	}
	if len(got) != 0 {
		t.Fatalf("stories length: got %d, want 0", len(got))
	}
}

func TestListStoriesHandler_ClientError(t *testing.T) {
	sentinel := errors.New("deadline exceeded")
	fc := &fakeFleetClient{storyErr: sentinel}
	h := NewListStoriesHandler(fc)

	_, _, err := h.Handle(context.Background(), "e-1", "", 10, 0)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !errors.Is(err, sentinel) {
		t.Fatalf("error chain should contain sentinel: got %v", err)
	}
	want := "list_stories: deadline exceeded"
	if err.Error() != want {
		t.Fatalf("error message: got %q, want %q", err.Error(), want)
	}
}

// ---------------------------------------------------------------------------
// ListTasksHandler tests
// ---------------------------------------------------------------------------

func TestListTasksHandler_Success(t *testing.T) {
	want := []domain.TaskSummary{
		{ID: "t-1", StoryID: "s-1", Title: "Write tests", Status: "in_progress", Priority: 1},
		{ID: "t-2", StoryID: "s-1", Title: "Code review", Status: "todo", Priority: 2},
		{ID: "t-3", StoryID: "s-1", Title: "Deploy", Status: "todo", Priority: 3},
	}
	fc := &fakeFleetClient{
		tasks:     want,
		taskTotal: 3,
	}
	h := NewListTasksHandler(fc)

	got, total, err := h.Handle(context.Background(), "s-1", "in_progress", 10, 0)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if total != 3 {
		t.Fatalf("total: got %d, want 3", total)
	}
	if len(got) != len(want) {
		t.Fatalf("tasks length: got %d, want %d", len(got), len(want))
	}
	for i := range want {
		if got[i].ID != want[i].ID {
			t.Errorf("task[%d].ID: got %q, want %q", i, got[i].ID, want[i].ID)
		}
		if got[i].Title != want[i].Title {
			t.Errorf("task[%d].Title: got %q, want %q", i, got[i].Title, want[i].Title)
		}
		if got[i].Priority != want[i].Priority {
			t.Errorf("task[%d].Priority: got %d, want %d", i, got[i].Priority, want[i].Priority)
		}
	}
}

func TestListTasksHandler_EmptyResult(t *testing.T) {
	fc := &fakeFleetClient{
		tasks:     nil,
		taskTotal: 0,
	}
	h := NewListTasksHandler(fc)

	got, total, err := h.Handle(context.Background(), "", "", 10, 0)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if total != 0 {
		t.Fatalf("total: got %d, want 0", total)
	}
	if len(got) != 0 {
		t.Fatalf("tasks length: got %d, want 0", len(got))
	}
}

func TestListTasksHandler_ClientError(t *testing.T) {
	sentinel := errors.New("permission denied")
	fc := &fakeFleetClient{taskErr: sentinel}
	h := NewListTasksHandler(fc)

	_, _, err := h.Handle(context.Background(), "s-1", "", 10, 0)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !errors.Is(err, sentinel) {
		t.Fatalf("error chain should contain sentinel: got %v", err)
	}
	want := "list_tasks: permission denied"
	if err.Error() != want {
		t.Fatalf("error message: got %q, want %q", err.Error(), want)
	}
}

// ---------------------------------------------------------------------------
// GetCeremonyHandler tests
// ---------------------------------------------------------------------------

func TestGetCeremonyHandler_Success(t *testing.T) {
	want := domain.CeremonyStatus{
		InstanceID:     "ci-42",
		CeremonyID:     "cer-1",
		StoryID:        "s-1",
		DefinitionName: "sprint_planning",
		CurrentState:   "step_2",
		Status:         "running",
		StepStatuses:   map[string]string{"step_1": "completed", "step_2": "running"},
		StepOutputs:    map[string]string{"step_1": "output-data"},
	}
	fc := &fakeFleetClient{ceremony: want}
	h := NewGetCeremonyHandler(fc)

	got, err := h.Handle(context.Background(), GetCeremonyQuery{InstanceID: "ci-42"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got.InstanceID != want.InstanceID {
		t.Errorf("InstanceID: got %q, want %q", got.InstanceID, want.InstanceID)
	}
	if got.CeremonyID != want.CeremonyID {
		t.Errorf("CeremonyID: got %q, want %q", got.CeremonyID, want.CeremonyID)
	}
	if got.StoryID != want.StoryID {
		t.Errorf("StoryID: got %q, want %q", got.StoryID, want.StoryID)
	}
	if got.DefinitionName != want.DefinitionName {
		t.Errorf("DefinitionName: got %q, want %q", got.DefinitionName, want.DefinitionName)
	}
	if got.CurrentState != want.CurrentState {
		t.Errorf("CurrentState: got %q, want %q", got.CurrentState, want.CurrentState)
	}
	if got.Status != want.Status {
		t.Errorf("Status: got %q, want %q", got.Status, want.Status)
	}
	if len(got.StepStatuses) != len(want.StepStatuses) {
		t.Errorf("StepStatuses length: got %d, want %d", len(got.StepStatuses), len(want.StepStatuses))
	}
	if len(got.StepOutputs) != len(want.StepOutputs) {
		t.Errorf("StepOutputs length: got %d, want %d", len(got.StepOutputs), len(want.StepOutputs))
	}
}

func TestGetCeremonyHandler_EmptyInstanceID(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewGetCeremonyHandler(fc)

	_, err := h.Handle(context.Background(), GetCeremonyQuery{InstanceID: ""})
	if err == nil {
		t.Fatal("expected error for empty instance_id, got nil")
	}
	want := "get_ceremony: instance_id is required"
	if err.Error() != want {
		t.Fatalf("error message: got %q, want %q", err.Error(), want)
	}
}

func TestGetCeremonyHandler_ClientError(t *testing.T) {
	sentinel := errors.New("not found")
	fc := &fakeFleetClient{ceremonyErr: sentinel}
	h := NewGetCeremonyHandler(fc)

	_, err := h.Handle(context.Background(), GetCeremonyQuery{InstanceID: "ci-99"})
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !errors.Is(err, sentinel) {
		t.Fatalf("error chain should contain sentinel: got %v", err)
	}
	want := "get_ceremony: not found"
	if err.Error() != want {
		t.Fatalf("error message: got %q, want %q", err.Error(), want)
	}
}

// ---------------------------------------------------------------------------
// WatchEventsHandler tests
// ---------------------------------------------------------------------------

func TestWatchEventsHandler_Success(t *testing.T) {
	ch := make(chan domain.FleetEvent, 4)
	fc := &fakeFleetClient{eventsCh: ch}
	h := NewWatchEventsHandler(fc)

	// Send an event before calling Handle so the channel is pre-populated.
	ev := domain.FleetEvent{
		Type:           "story.created",
		IdempotencyKey: "key-1",
		CorrelationID:  "corr-1",
		Timestamp:      "2026-03-05T10:00:00Z",
		Producer:       "agent-alpha",
		Payload:        []byte(`{"id":"s-1"}`),
	}
	ch <- ev

	q := WatchEventsQuery{
		EventTypes: []string{"story.created"},
		ProjectID:  "proj-1",
	}
	got, err := h.Handle(context.Background(), q)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got == nil {
		t.Fatal("expected non-nil channel")
	}

	received := <-got
	if received.Type != ev.Type {
		t.Errorf("event Type: got %q, want %q", received.Type, ev.Type)
	}
	if received.IdempotencyKey != ev.IdempotencyKey {
		t.Errorf("event IdempotencyKey: got %q, want %q", received.IdempotencyKey, ev.IdempotencyKey)
	}
	if received.CorrelationID != ev.CorrelationID {
		t.Errorf("event CorrelationID: got %q, want %q", received.CorrelationID, ev.CorrelationID)
	}
	if received.Producer != ev.Producer {
		t.Errorf("event Producer: got %q, want %q", received.Producer, ev.Producer)
	}
}

func TestWatchEventsHandler_NilEventsCh(t *testing.T) {
	// When eventsCh is nil the fake allocates one internally.
	fc := &fakeFleetClient{}
	h := NewWatchEventsHandler(fc)

	got, err := h.Handle(context.Background(), WatchEventsQuery{})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got == nil {
		t.Fatal("expected non-nil channel even when fake starts with nil eventsCh")
	}
}

func TestWatchEventsHandler_ClientError(t *testing.T) {
	sentinel := errors.New("stream unavailable")
	fc := &fakeFleetClient{eventsErr: sentinel}
	h := NewWatchEventsHandler(fc)

	_, err := h.Handle(context.Background(), WatchEventsQuery{
		EventTypes: []string{"ceremony.started"},
		ProjectID:  "proj-1",
	})
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !errors.Is(err, sentinel) {
		t.Fatalf("error chain should contain sentinel: got %v", err)
	}
	want := "watch_events: stream unavailable"
	if err.Error() != want {
		t.Fatalf("error message: got %q, want %q", err.Error(), want)
	}
}

func TestWatchEventsHandler_MultipleEvents(t *testing.T) {
	ch := make(chan domain.FleetEvent, 4)
	fc := &fakeFleetClient{eventsCh: ch}
	h := NewWatchEventsHandler(fc)

	events := []domain.FleetEvent{
		{Type: "story.created", IdempotencyKey: "k1"},
		{Type: "task.assigned", IdempotencyKey: "k2"},
		{Type: "ceremony.completed", IdempotencyKey: "k3"},
	}
	for _, e := range events {
		ch <- e
	}

	got, err := h.Handle(context.Background(), WatchEventsQuery{})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	for i, want := range events {
		received := <-got
		if received.Type != want.Type {
			t.Errorf("event[%d].Type: got %q, want %q", i, received.Type, want.Type)
		}
		if received.IdempotencyKey != want.IdempotencyKey {
			t.Errorf("event[%d].IdempotencyKey: got %q, want %q", i, received.IdempotencyKey, want.IdempotencyKey)
		}
	}
}

// ---------------------------------------------------------------------------
// ListEpicsHandler tests
// ---------------------------------------------------------------------------

func TestListEpicsHandler_Success(t *testing.T) {
	want := []domain.EpicSummary{
		{ID: "ep-1", ProjectID: "p-1", Title: "Auth module", Description: "Authentication epic", Status: "active"},
		{ID: "ep-2", ProjectID: "p-1", Title: "Billing", Description: "Billing epic", Status: "draft"},
	}
	fc := &fakeFleetClient{
		epics:     want,
		epicTotal: 2,
	}
	h := NewListEpicsHandler(fc)

	got, total, err := h.Handle(context.Background(), "p-1", "active", 10, 0)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if total != 2 {
		t.Fatalf("total: got %d, want 2", total)
	}
	if len(got) != len(want) {
		t.Fatalf("epics length: got %d, want %d", len(got), len(want))
	}
	for i := range want {
		if got[i].ID != want[i].ID {
			t.Errorf("epic[%d].ID: got %q, want %q", i, got[i].ID, want[i].ID)
		}
		if got[i].Title != want[i].Title {
			t.Errorf("epic[%d].Title: got %q, want %q", i, got[i].Title, want[i].Title)
		}
		if got[i].ProjectID != want[i].ProjectID {
			t.Errorf("epic[%d].ProjectID: got %q, want %q", i, got[i].ProjectID, want[i].ProjectID)
		}
	}
}

func TestListEpicsHandler_EmptyResult(t *testing.T) {
	fc := &fakeFleetClient{
		epics:     nil,
		epicTotal: 0,
	}
	h := NewListEpicsHandler(fc)

	got, total, err := h.Handle(context.Background(), "", "", 10, 0)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if total != 0 {
		t.Fatalf("total: got %d, want 0", total)
	}
	if len(got) != 0 {
		t.Fatalf("epics length: got %d, want 0", len(got))
	}
}

func TestListEpicsHandler_ClientError(t *testing.T) {
	sentinel := errors.New("timeout")
	fc := &fakeFleetClient{epicErr: sentinel}
	h := NewListEpicsHandler(fc)

	_, _, err := h.Handle(context.Background(), "p-1", "", 10, 0)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !errors.Is(err, sentinel) {
		t.Fatalf("error chain should contain sentinel: got %v", err)
	}
	want := "list_epics: timeout"
	if err.Error() != want {
		t.Fatalf("error message: got %q, want %q", err.Error(), want)
	}
}

// ---------------------------------------------------------------------------
// ListCeremoniesHandler tests
// ---------------------------------------------------------------------------

func TestListCeremoniesHandler_Success(t *testing.T) {
	want := []domain.CeremonyStatus{
		{
			InstanceID:     "ci-1",
			CeremonyID:     "cer-10",
			StoryID:        "s-1",
			DefinitionName: "sprint_planning",
			CurrentState:   "step_2",
			Status:         "running",
			StepStatuses:   map[string]string{"step_1": "completed", "step_2": "running"},
			StepOutputs:    map[string]string{"step_1": "output-1"},
		},
		{
			InstanceID:     "ci-2",
			CeremonyID:     "cer-20",
			StoryID:        "s-2",
			DefinitionName: "backlog_review",
			CurrentState:   "step_1",
			Status:         "pending",
		},
	}
	fc := &fakeFleetClient{
		ceremonies:    want,
		ceremonyTotal: 2,
	}
	h := NewListCeremoniesHandler(fc)

	got, total, err := h.Handle(context.Background(), "s-1", "running", 10, 0)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if total != 2 {
		t.Fatalf("total: got %d, want 2", total)
	}
	if len(got) != len(want) {
		t.Fatalf("ceremonies length: got %d, want %d", len(got), len(want))
	}
	for i := range want {
		if got[i].InstanceID != want[i].InstanceID {
			t.Errorf("ceremony[%d].InstanceID: got %q, want %q", i, got[i].InstanceID, want[i].InstanceID)
		}
		if got[i].CeremonyID != want[i].CeremonyID {
			t.Errorf("ceremony[%d].CeremonyID: got %q, want %q", i, got[i].CeremonyID, want[i].CeremonyID)
		}
		if got[i].Status != want[i].Status {
			t.Errorf("ceremony[%d].Status: got %q, want %q", i, got[i].Status, want[i].Status)
		}
	}
}

func TestListCeremoniesHandler_EmptyResult(t *testing.T) {
	fc := &fakeFleetClient{
		ceremonies:    nil,
		ceremonyTotal: 0,
	}
	h := NewListCeremoniesHandler(fc)

	got, total, err := h.Handle(context.Background(), "", "", 10, 0)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if total != 0 {
		t.Fatalf("total: got %d, want 0", total)
	}
	if len(got) != 0 {
		t.Fatalf("ceremonies length: got %d, want 0", len(got))
	}
}

func TestListCeremoniesHandler_ClientError(t *testing.T) {
	sentinel := errors.New("unavailable")
	fc := &fakeFleetClient{ceremoniesErr: sentinel}
	h := NewListCeremoniesHandler(fc)

	_, _, err := h.Handle(context.Background(), "s-1", "", 10, 0)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !errors.Is(err, sentinel) {
		t.Fatalf("error chain should contain sentinel: got %v", err)
	}
	want := "list_ceremonies: unavailable"
	if err.Error() != want {
		t.Fatalf("error message: got %q, want %q", err.Error(), want)
	}
}

// ---------------------------------------------------------------------------
// GetBacklogReviewHandler tests
// ---------------------------------------------------------------------------

func TestGetBacklogReviewHandler_Success(t *testing.T) {
	want := domain.BacklogReview{
		CeremonyID: "cer-br-1",
		Status:     "in_progress",
	}
	fc := &fakeFleetClient{backlogReview: want}
	h := NewGetBacklogReviewHandler(fc)

	got, err := h.Handle(context.Background(), GetBacklogReviewQuery{CeremonyID: "cer-br-1"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got.CeremonyID != want.CeremonyID {
		t.Errorf("CeremonyID: got %q, want %q", got.CeremonyID, want.CeremonyID)
	}
	if got.Status != want.Status {
		t.Errorf("Status: got %q, want %q", got.Status, want.Status)
	}
}

func TestGetBacklogReviewHandler_EmptyCeremonyID(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewGetBacklogReviewHandler(fc)

	_, err := h.Handle(context.Background(), GetBacklogReviewQuery{CeremonyID: ""})
	if err == nil {
		t.Fatal("expected error for empty ceremony_id, got nil")
	}
	want := "get_backlog_review: ceremony_id is required"
	if err.Error() != want {
		t.Fatalf("error message: got %q, want %q", err.Error(), want)
	}
}

func TestGetBacklogReviewHandler_ClientError(t *testing.T) {
	sentinel := errors.New("not found")
	fc := &fakeFleetClient{backlogReviewErr: sentinel}
	h := NewGetBacklogReviewHandler(fc)

	_, err := h.Handle(context.Background(), GetBacklogReviewQuery{CeremonyID: "cer-br-99"})
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !errors.Is(err, sentinel) {
		t.Fatalf("error chain should contain sentinel: got %v", err)
	}
	want := "get_backlog_review: not found"
	if err.Error() != want {
		t.Fatalf("error message: got %q, want %q", err.Error(), want)
	}
}

// ---------------------------------------------------------------------------
// ListBacklogReviewsHandler tests
// ---------------------------------------------------------------------------

func TestListBacklogReviewsHandler_Success(t *testing.T) {
	want := []domain.BacklogReview{
		{CeremonyID: "cer-br-1", Status: "completed"},
		{CeremonyID: "cer-br-2", Status: "in_progress"},
	}
	fc := &fakeFleetClient{
		backlogReviews:     want,
		backlogReviewTotal: 2,
	}
	h := NewListBacklogReviewsHandler(fc)

	got, total, err := h.Handle(context.Background(), "completed", 10, 0)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if total != 2 {
		t.Fatalf("total: got %d, want 2", total)
	}
	if len(got) != len(want) {
		t.Fatalf("reviews length: got %d, want %d", len(got), len(want))
	}
	for i := range want {
		if got[i].CeremonyID != want[i].CeremonyID {
			t.Errorf("review[%d].CeremonyID: got %q, want %q", i, got[i].CeremonyID, want[i].CeremonyID)
		}
		if got[i].Status != want[i].Status {
			t.Errorf("review[%d].Status: got %q, want %q", i, got[i].Status, want[i].Status)
		}
	}
}

func TestListBacklogReviewsHandler_EmptyResult(t *testing.T) {
	fc := &fakeFleetClient{
		backlogReviews:     nil,
		backlogReviewTotal: 0,
	}
	h := NewListBacklogReviewsHandler(fc)

	got, total, err := h.Handle(context.Background(), "", 10, 0)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if total != 0 {
		t.Fatalf("total: got %d, want 0", total)
	}
	if len(got) != 0 {
		t.Fatalf("reviews length: got %d, want 0", len(got))
	}
}

func TestListBacklogReviewsHandler_ClientError(t *testing.T) {
	sentinel := errors.New("internal error")
	fc := &fakeFleetClient{backlogReviewsErr: sentinel}
	h := NewListBacklogReviewsHandler(fc)

	_, _, err := h.Handle(context.Background(), "", 10, 0)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !errors.Is(err, sentinel) {
		t.Fatalf("error chain should contain sentinel: got %v", err)
	}
	want := "list_backlog_reviews: internal error"
	if err.Error() != want {
		t.Fatalf("error message: got %q, want %q", err.Error(), want)
	}
}
