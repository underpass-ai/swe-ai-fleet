package app

import (
	"context"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain/identity"
)

// --- minimal fakes for wiring test ---

type fakeFleetClient struct{}

func (f *fakeFleetClient) Enroll(context.Context, string, string, []byte) ([]byte, []byte, string, string, error) {
	return nil, nil, "", "", nil
}
func (f *fakeFleetClient) Renew(context.Context, []byte) ([]byte, []byte, string, error) {
	return nil, nil, "", nil
}
func (f *fakeFleetClient) CreateProject(context.Context, string, string, string) (domain.ProjectSummary, error) {
	return domain.ProjectSummary{}, nil
}
func (f *fakeFleetClient) CreateEpic(context.Context, string, string, string, string) (domain.EpicSummary, error) {
	return domain.EpicSummary{}, nil
}
func (f *fakeFleetClient) CreateStory(context.Context, string, string, string, string) (domain.StorySummary, error) {
	return domain.StorySummary{}, nil
}
func (f *fakeFleetClient) CreateTask(context.Context, ports.CreateTaskInput) (domain.TaskSummary, error) {
	return domain.TaskSummary{}, nil
}
func (f *fakeFleetClient) TransitionStory(context.Context, string, string) error { return nil }
func (f *fakeFleetClient) StartCeremony(context.Context, string, string, string, string, []string) (domain.CeremonyStatus, error) {
	return domain.CeremonyStatus{}, nil
}
func (f *fakeFleetClient) ApproveDecision(context.Context, string, string, string) error { return nil }
func (f *fakeFleetClient) RejectDecision(context.Context, string, string, string) error  { return nil }
func (f *fakeFleetClient) ListProjects(context.Context, string, int32, int32) ([]domain.ProjectSummary, int32, error) {
	return nil, 0, nil
}
func (f *fakeFleetClient) ListEpics(context.Context, string, string, int32, int32) ([]domain.EpicSummary, int32, error) {
	return nil, 0, nil
}
func (f *fakeFleetClient) ListStories(context.Context, string, string, int32, int32) ([]domain.StorySummary, int32, error) {
	return nil, 0, nil
}
func (f *fakeFleetClient) ListTasks(context.Context, string, string, int32, int32) ([]domain.TaskSummary, int32, error) {
	return nil, 0, nil
}
func (f *fakeFleetClient) ListCeremonies(context.Context, string, string, int32, int32) ([]domain.CeremonyStatus, int32, error) {
	return nil, 0, nil
}
func (f *fakeFleetClient) GetCeremony(context.Context, string) (domain.CeremonyStatus, error) {
	return domain.CeremonyStatus{}, nil
}
func (f *fakeFleetClient) WatchEvents(context.Context, []string, string) (<-chan domain.FleetEvent, error) {
	return nil, nil
}
func (f *fakeFleetClient) CreateBacklogReview(context.Context, string, []string) (domain.BacklogReview, error) {
	return domain.BacklogReview{}, nil
}
func (f *fakeFleetClient) StartBacklogReview(context.Context, string, string) (domain.BacklogReview, int32, error) {
	return domain.BacklogReview{}, 0, nil
}
func (f *fakeFleetClient) ApproveReviewPlan(context.Context, ports.ApproveReviewPlanInput) (domain.BacklogReview, string, error) {
	return domain.BacklogReview{}, "", nil
}
func (f *fakeFleetClient) RejectReviewPlan(context.Context, string, string, string, string) (domain.BacklogReview, error) {
	return domain.BacklogReview{}, nil
}
func (f *fakeFleetClient) CompleteBacklogReview(context.Context, string, string) (domain.BacklogReview, error) {
	return domain.BacklogReview{}, nil
}
func (f *fakeFleetClient) CancelBacklogReview(context.Context, string, string) (domain.BacklogReview, error) {
	return domain.BacklogReview{}, nil
}
func (f *fakeFleetClient) GetBacklogReview(context.Context, string) (domain.BacklogReview, error) {
	return domain.BacklogReview{}, nil
}
func (f *fakeFleetClient) ListBacklogReviews(context.Context, string, int32, int32) ([]domain.BacklogReview, int32, error) {
	return nil, 0, nil
}
func (f *fakeFleetClient) Close() error { return nil }

type fakeCredStore struct{}

func (f *fakeCredStore) Save([]byte, []byte, []byte, string) error       { return nil }
func (f *fakeCredStore) Load() (identity.Credentials, error)             { return identity.Credentials{}, nil }
func (f *fakeCredStore) Exists() bool                                     { return false }

type fakeCfgStore struct{}

func (f *fakeCfgStore) Load() (domain.Config, error) { return domain.Config{}, nil }
func (f *fakeCfgStore) Save(domain.Config) error      { return nil }

func TestNewHandlers_AllFieldsPopulated(t *testing.T) {
	h := NewHandlers(&fakeFleetClient{}, &fakeCredStore{}, &fakeCfgStore{})

	checks := []struct {
		name string
		ptr  interface{}
	}{
		{"Enroll", h.Enroll},
		{"Renew", h.Renew},
		{"CreateProject", h.CreateProject},
		{"CreateEpic", h.CreateEpic},
		{"CreateStory", h.CreateStory},
		{"CreateTask", h.CreateTask},
		{"TransitionStory", h.TransitionStory},
		{"StartCeremony", h.StartCeremony},
		{"ApproveDecision", h.ApproveDecision},
		{"RejectDecision", h.RejectDecision},
		{"CreateBacklogReview", h.CreateBacklogReview},
		{"StartBacklogReview", h.StartBacklogReview},
		{"ApproveReviewPlan", h.ApproveReviewPlan},
		{"RejectReviewPlan", h.RejectReviewPlan},
		{"CompleteBacklogReview", h.CompleteBacklogReview},
		{"CancelBacklogReview", h.CancelBacklogReview},
		{"ListProjects", h.ListProjects},
		{"ListEpics", h.ListEpics},
		{"ListStories", h.ListStories},
		{"ListTasks", h.ListTasks},
		{"ListCeremonies", h.ListCeremonies},
		{"GetCeremony", h.GetCeremony},
		{"WatchEvents", h.WatchEvents},
		{"GetBacklogReview", h.GetBacklogReview},
		{"ListBacklogReviews", h.ListBacklogReviews},
	}
	for _, c := range checks {
		if c.ptr == nil {
			t.Errorf("%s handler is nil", c.name)
		}
	}
}
