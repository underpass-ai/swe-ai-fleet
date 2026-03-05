package command

import (
	"context"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

// ---------------------------------------------------------------------------
// Shared hand-written fakes for command handler tests.
// ---------------------------------------------------------------------------

// flexPlanningClient is a flexible fake that lets each test case configure
// the return values for the specific method under test.
type flexPlanningClient struct {
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

	// List (unused in command tests; stubs for interface compliance)
}

func (f *flexPlanningClient) CreateProject(_ context.Context, _, _, _ string) (string, error) {
	return f.createProjectID, f.createProjectErr
}

func (f *flexPlanningClient) CreateEpic(_ context.Context, _, _, _ string) (string, error) {
	return f.createEpicID, f.createEpicErr
}

func (f *flexPlanningClient) CreateStory(_ context.Context, _, _, _, _ string) (string, error) {
	return f.createStoryID, f.createStoryErr
}

// flexUserClient is a flexible fake for the UserClient port.
type flexUserClient struct {
	createResult ports.UserResult
	createErr    error
	getResult    ports.UserResult
	getErr       error
}

func (f *flexUserClient) CreateUser(_ context.Context, _, _, _, _, _ string) (ports.UserResult, error) {
	return f.createResult, f.createErr
}

func (f *flexUserClient) GetUserByClientID(_ context.Context, _ string) (ports.UserResult, error) {
	return f.getResult, f.getErr
}

func (f *flexPlanningClient) TransitionStory(_ context.Context, _, _ string) error {
	return f.transitionStoryErr
}

func (f *flexPlanningClient) CreateTask(_ context.Context, _, _, _, _, _, _ string, _, _ int32) (string, error) {
	return f.createTaskID, f.createTaskErr
}

func (f *flexPlanningClient) ApproveDecision(_ context.Context, _, _, _, _ string) error {
	return f.approveDecisionErr
}

func (f *flexPlanningClient) RejectDecision(_ context.Context, _, _, _, _ string) error {
	return f.rejectDecisionErr
}

func (f *flexPlanningClient) ListProjects(_ context.Context, _ string, _, _ int32) ([]ports.ProjectResult, int32, error) {
	return nil, 0, nil
}

func (f *flexPlanningClient) ListEpics(_ context.Context, _, _ string, _, _ int32) ([]ports.EpicResult, int32, error) {
	return nil, 0, nil
}

func (f *flexPlanningClient) ListStories(_ context.Context, _, _ string, _, _ int32) ([]ports.StoryResult, int32, error) {
	return nil, 0, nil
}

func (f *flexPlanningClient) ListTasks(_ context.Context, _, _ string, _, _ int32) ([]ports.TaskResult, int32, error) {
	return nil, 0, nil
}

func (f *flexPlanningClient) CreateBacklogReview(_ context.Context, _ string, _ []string) (ports.BacklogReviewResult, error) {
	return f.createBacklogReviewResult, f.createBacklogReviewErr
}

func (f *flexPlanningClient) StartBacklogReview(_ context.Context, _, _ string) (ports.BacklogReviewResult, int32, error) {
	return f.startBacklogReviewResult, f.startBacklogReviewCount, f.startBacklogReviewErr
}

func (f *flexPlanningClient) GetBacklogReview(_ context.Context, _ string) (ports.BacklogReviewResult, error) {
	return f.getBacklogResult, f.getBacklogErr
}

func (f *flexPlanningClient) ListBacklogReviews(_ context.Context, _ string, _, _ int32) ([]ports.BacklogReviewResult, int32, error) {
	return f.listBacklogResults, f.listBacklogTotal, f.listBacklogErr
}

func (f *flexPlanningClient) ApproveReviewPlan(_ context.Context, _, _, _, _, _, _, _ string) (ports.BacklogReviewResult, string, error) {
	return f.approveReviewPlanResult, f.approveReviewPlanID, f.approveReviewPlanErr
}

func (f *flexPlanningClient) RejectReviewPlan(_ context.Context, _, _, _, _ string) (ports.BacklogReviewResult, error) {
	return f.rejectReviewPlanResult, f.rejectReviewPlanErr
}

func (f *flexPlanningClient) CompleteBacklogReview(_ context.Context, _, _ string) (ports.BacklogReviewResult, error) {
	return f.completeBacklogResult, f.completeBacklogErr
}

func (f *flexPlanningClient) CancelBacklogReview(_ context.Context, _, _ string) (ports.BacklogReviewResult, error) {
	return f.cancelBacklogResult, f.cancelBacklogErr
}

// flexCeremonyClient is a flexible fake for the CeremonyClient port.
type flexCeremonyClient struct {
	startCeremonyID  string
	startCeremonyErr error

	startBacklogReviewCount int32
	startBacklogReviewErr   error
}

func (f *flexCeremonyClient) StartCeremony(_ context.Context, _, _, _ string, _ []string) (string, error) {
	return f.startCeremonyID, f.startCeremonyErr
}

func (f *flexCeremonyClient) StartBacklogReview(_ context.Context, _ string) (int32, error) {
	return f.startBacklogReviewCount, f.startBacklogReviewErr
}

func (f *flexCeremonyClient) GetCeremony(_ context.Context, _ string) (ports.CeremonyResult, error) {
	return ports.CeremonyResult{}, nil
}

func (f *flexCeremonyClient) ListCeremonies(_ context.Context, _, _ string, _, _ int32) ([]ports.CeremonyResult, int32, error) {
	return nil, 0, nil
}
