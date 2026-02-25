package query

import (
	"context"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/event"
)

// ---------------------------------------------------------------------------
// Shared hand-written fakes for query handler tests.
// ---------------------------------------------------------------------------

// fakePlanningClient is a flexible fake for the PlanningClient port
// that returns canned data for list/query operations.
type fakePlanningClient struct {
	// List results
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

func (f *fakePlanningClient) CreateProject(_ context.Context, _, _ string) (string, error) {
	return "", nil
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
	return f.projects, f.projectTotal, f.projectErr
}

func (f *fakePlanningClient) ListEpics(_ context.Context, _, _ string, _, _ int32) ([]ports.EpicResult, int32, error) {
	return f.epics, f.epicTotal, f.epicErr
}

func (f *fakePlanningClient) ListStories(_ context.Context, _, _ string, _, _ int32) ([]ports.StoryResult, int32, error) {
	return f.stories, f.storyTotal, f.storyErr
}

func (f *fakePlanningClient) ListTasks(_ context.Context, _, _ string, _, _ int32) ([]ports.TaskResult, int32, error) {
	return f.tasks, f.taskTotal, f.taskErr
}

// fakeCeremonyClient is a flexible fake for the CeremonyClient port.
type fakeCeremonyClient struct {
	ceremony     ports.CeremonyResult
	ceremonyErr  error
	ceremonies   []ports.CeremonyResult
	ceremonyList int32
	listErr      error
}

func (f *fakeCeremonyClient) StartCeremony(_ context.Context, _, _, _ string, _ []string) (string, error) {
	return "", nil
}

func (f *fakeCeremonyClient) StartBacklogReview(_ context.Context, _ string) (int32, error) {
	return 0, nil
}

func (f *fakeCeremonyClient) GetCeremony(_ context.Context, _ string) (ports.CeremonyResult, error) {
	return f.ceremony, f.ceremonyErr
}

func (f *fakeCeremonyClient) ListCeremonies(_ context.Context, _, _ string, _, _ int32) ([]ports.CeremonyResult, int32, error) {
	return f.ceremonies, f.ceremonyList, f.listErr
}

// fakeEventSubscriber is a fake for the EventSubscriber port.
type fakeEventSubscriber struct {
	ch  chan event.FleetEvent
	err error
}

func (f *fakeEventSubscriber) Subscribe(_ context.Context, _ event.EventFilter) (<-chan event.FleetEvent, error) {
	if f.err != nil {
		return nil, f.err
	}
	return f.ch, nil
}

func (f *fakeEventSubscriber) Close() error {
	return nil
}
