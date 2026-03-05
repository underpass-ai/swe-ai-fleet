package grpcapi

import (
	"context"

	"google.golang.org/grpc/metadata"

	proxyv1 "github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/gen/proxyv1"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/event"
)

// ---------------------------------------------------------------------------
// Shared hand-written fakes for gRPC service adapter tests.
// ---------------------------------------------------------------------------

// fakeAuditLogger is a no-op audit logger.
type fakeAuditLogger struct{}

func (f *fakeAuditLogger) Record(_ context.Context, _ ports.AuditEvent) {}

// ---------------------------------------------------------------------------
// fakePlanningClientCmd implements ports.PlanningClient with configurable returns.
// ---------------------------------------------------------------------------

type fakePlanningClientCmd struct {
	// Project
	createProjectID  string
	createProjectErr error

	// Epic
	createEpicID  string
	createEpicErr error

	// Story
	createStoryID      string
	createStoryErr     error
	transitionStoryErr error

	// Task
	createTaskID  string
	createTaskErr error

	// Decision
	approveDecisionErr error
	rejectDecisionErr  error

	// Backlog Review
	createBacklogReviewResult ports.BacklogReviewResult
	createBacklogReviewErr    error
	startBacklogReviewResult  ports.BacklogReviewResult
	startBacklogReviewCount   int32
	startBacklogReviewErr     error
	approveReviewPlanResult   ports.BacklogReviewResult
	approveReviewPlanID       string
	approveReviewPlanErr      error
	rejectReviewPlanResult    ports.BacklogReviewResult
	rejectReviewPlanErr       error
	completeBacklogResult     ports.BacklogReviewResult
	completeBacklogErr        error
	cancelBacklogResult       ports.BacklogReviewResult
	cancelBacklogErr          error
	getBacklogResult          ports.BacklogReviewResult
	getBacklogErr             error
	listBacklogResults        []ports.BacklogReviewResult
	listBacklogTotal          int32
	listBacklogErr            error

	// List queries
	projects     []ports.ProjectResult
	projectTotal int32
	projectErr   error

	epics     []ports.EpicResult
	epicTotal int32
	epicErr   error

	stories    []ports.StoryResult
	storyTotal int32
	storyErr   error

	tasks     []ports.TaskResult
	taskTotal int32
	taskErr   error
}

func (f *fakePlanningClientCmd) CreateProject(_ context.Context, _, _, _ string) (string, error) {
	return f.createProjectID, f.createProjectErr
}

func (f *fakePlanningClientCmd) CreateEpic(_ context.Context, _, _, _ string) (string, error) {
	return f.createEpicID, f.createEpicErr
}

func (f *fakePlanningClientCmd) CreateStory(_ context.Context, _, _, _, _ string) (string, error) {
	return f.createStoryID, f.createStoryErr
}

func (f *fakePlanningClientCmd) TransitionStory(_ context.Context, _, _ string) error {
	return f.transitionStoryErr
}

func (f *fakePlanningClientCmd) CreateTask(_ context.Context, _, _, _, _, _, _ string, _, _ int32) (string, error) {
	return f.createTaskID, f.createTaskErr
}

func (f *fakePlanningClientCmd) ApproveDecision(_ context.Context, _, _, _, _ string) error {
	return f.approveDecisionErr
}

func (f *fakePlanningClientCmd) RejectDecision(_ context.Context, _, _, _, _ string) error {
	return f.rejectDecisionErr
}

func (f *fakePlanningClientCmd) ListProjects(_ context.Context, _ string, _, _ int32) ([]ports.ProjectResult, int32, error) {
	return f.projects, f.projectTotal, f.projectErr
}

func (f *fakePlanningClientCmd) ListEpics(_ context.Context, _, _ string, _, _ int32) ([]ports.EpicResult, int32, error) {
	return f.epics, f.epicTotal, f.epicErr
}

func (f *fakePlanningClientCmd) ListStories(_ context.Context, _, _ string, _, _ int32) ([]ports.StoryResult, int32, error) {
	return f.stories, f.storyTotal, f.storyErr
}

func (f *fakePlanningClientCmd) ListTasks(_ context.Context, _, _ string, _, _ int32) ([]ports.TaskResult, int32, error) {
	return f.tasks, f.taskTotal, f.taskErr
}

func (f *fakePlanningClientCmd) CreateBacklogReview(_ context.Context, _ string, _ []string) (ports.BacklogReviewResult, error) {
	return f.createBacklogReviewResult, f.createBacklogReviewErr
}

func (f *fakePlanningClientCmd) StartBacklogReview(_ context.Context, _, _ string) (ports.BacklogReviewResult, int32, error) {
	return f.startBacklogReviewResult, f.startBacklogReviewCount, f.startBacklogReviewErr
}

func (f *fakePlanningClientCmd) GetBacklogReview(_ context.Context, _ string) (ports.BacklogReviewResult, error) {
	return f.getBacklogResult, f.getBacklogErr
}

func (f *fakePlanningClientCmd) ListBacklogReviews(_ context.Context, _ string, _, _ int32) ([]ports.BacklogReviewResult, int32, error) {
	return f.listBacklogResults, f.listBacklogTotal, f.listBacklogErr
}

func (f *fakePlanningClientCmd) ApproveReviewPlan(_ context.Context, _, _, _, _, _, _, _ string) (ports.BacklogReviewResult, string, error) {
	return f.approveReviewPlanResult, f.approveReviewPlanID, f.approveReviewPlanErr
}

func (f *fakePlanningClientCmd) RejectReviewPlan(_ context.Context, _, _, _, _ string) (ports.BacklogReviewResult, error) {
	return f.rejectReviewPlanResult, f.rejectReviewPlanErr
}

func (f *fakePlanningClientCmd) CompleteBacklogReview(_ context.Context, _, _ string) (ports.BacklogReviewResult, error) {
	return f.completeBacklogResult, f.completeBacklogErr
}

func (f *fakePlanningClientCmd) CancelBacklogReview(_ context.Context, _, _ string) (ports.BacklogReviewResult, error) {
	return f.cancelBacklogResult, f.cancelBacklogErr
}

// ---------------------------------------------------------------------------
// fakeCeremonyClientCmd implements ports.CeremonyClient with configurable returns.
// ---------------------------------------------------------------------------

type fakeCeremonyClientCmd struct {
	startCeremonyID  string
	startCeremonyErr error

	getCeremony    ports.CeremonyResult
	getCeremonyErr error

	ceremonies   []ports.CeremonyResult
	ceremonyList int32
	listErr      error
}

func (f *fakeCeremonyClientCmd) StartCeremony(_ context.Context, _, _, _ string, _ []string) (string, error) {
	return f.startCeremonyID, f.startCeremonyErr
}

func (f *fakeCeremonyClientCmd) StartBacklogReview(_ context.Context, _ string) (int32, error) {
	return 0, nil
}

func (f *fakeCeremonyClientCmd) GetCeremony(_ context.Context, _ string) (ports.CeremonyResult, error) {
	return f.getCeremony, f.getCeremonyErr
}

func (f *fakeCeremonyClientCmd) ListCeremonies(_ context.Context, _, _ string, _, _ int32) ([]ports.CeremonyResult, int32, error) {
	return f.ceremonies, f.ceremonyList, f.listErr
}

// ---------------------------------------------------------------------------
// fakeEventSubscriberGRPC implements ports.EventSubscriber for WatchEvents tests.
// ---------------------------------------------------------------------------

type fakeEventSubscriberGRPC struct {
	ch  chan event.FleetEvent
	err error
}

func (f *fakeEventSubscriberGRPC) Subscribe(_ context.Context, _ event.EventFilter) (<-chan event.FleetEvent, error) {
	if f.err != nil {
		return nil, f.err
	}
	return f.ch, nil
}

func (f *fakeEventSubscriberGRPC) Close() error {
	return nil
}

// ---------------------------------------------------------------------------
// fakeWatchStream implements grpc.ServerStreamingServer[proxyv1.FleetEvent]
// for WatchEvents tests.
// ---------------------------------------------------------------------------

type fakeWatchStream struct {
	ctx     context.Context
	sent    []*proxyv1.FleetEvent
	sendErr error
}

func (f *fakeWatchStream) Send(evt *proxyv1.FleetEvent) error {
	if f.sendErr != nil {
		return f.sendErr
	}
	f.sent = append(f.sent, evt)
	return nil
}

func (f *fakeWatchStream) SetHeader(_ metadata.MD) error { return nil }
func (f *fakeWatchStream) SendHeader(_ metadata.MD) error { return nil }
func (f *fakeWatchStream) SetTrailer(_ metadata.MD)       {}
func (f *fakeWatchStream) Context() context.Context        { return f.ctx }
func (f *fakeWatchStream) SendMsg(_ any) error             { return nil }
func (f *fakeWatchStream) RecvMsg(_ any) error             { return nil }
