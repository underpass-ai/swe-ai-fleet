package views

import (
	"context"
	"fmt"
	"strings"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// fakeFleetClient implements ports.FleetClient for testing.
type fakeFleetClient struct {
	projects       []domain.ProjectSummary
	epics          []domain.EpicSummary
	stories        []domain.StorySummary
	tasks          []domain.TaskSummary
	ceremonies     []domain.CeremonyStatus
	events         chan domain.FleetEvent
	backlogReviews []domain.BacklogReview
	backlogReview  *domain.BacklogReview

	approveErr error
	rejectErr  error
	listErr    error
}

func (f *fakeFleetClient) Enroll(context.Context, string, string, []byte) ([]byte, []byte, string, string, error) {
	return nil, nil, "", "", fmt.Errorf("not implemented")
}

func (f *fakeFleetClient) Renew(context.Context, []byte) ([]byte, []byte, string, error) {
	return nil, nil, "", fmt.Errorf("not implemented")
}

func (f *fakeFleetClient) CreateProject(_ context.Context, _, _, _ string) (domain.ProjectSummary, error) {
	return domain.ProjectSummary{}, fmt.Errorf("not implemented")
}

func (f *fakeFleetClient) CreateEpic(_ context.Context, _, _, _, _ string) (domain.EpicSummary, error) {
	return domain.EpicSummary{}, fmt.Errorf("not implemented")
}

func (f *fakeFleetClient) CreateStory(_ context.Context, _, _, _, _ string) (domain.StorySummary, error) {
	return domain.StorySummary{}, fmt.Errorf("not implemented")
}

func (f *fakeFleetClient) CreateTask(_ context.Context, _, _, _, _, _, _ string, _, _ int32) (domain.TaskSummary, error) {
	return domain.TaskSummary{}, fmt.Errorf("not implemented")
}

func (f *fakeFleetClient) TransitionStory(context.Context, string, string) error {
	return nil
}

func (f *fakeFleetClient) StartCeremony(_ context.Context, _, _, _, _ string, _ []string) (domain.CeremonyStatus, error) {
	return domain.CeremonyStatus{}, fmt.Errorf("not implemented")
}

func (f *fakeFleetClient) ListProjects(_ context.Context, statusFilter string, limit, offset int32) ([]domain.ProjectSummary, int32, error) {
	if f.listErr != nil {
		return nil, 0, f.listErr
	}
	src := f.projects
	if statusFilter != "" && statusFilter != "ALL" {
		filtered := make([]domain.ProjectSummary, 0, len(src))
		for _, p := range src {
			if strings.EqualFold(p.Status, statusFilter) {
				filtered = append(filtered, p)
			}
		}
		src = filtered
	}
	total := int32(len(src))
	if limit <= 0 {
		return src, total, nil
	}
	start := int(offset)
	if start >= len(src) {
		return nil, total, nil
	}
	end := start + int(limit)
	if end > len(src) {
		end = len(src)
	}
	return src[start:end], total, nil
}

func (f *fakeFleetClient) ListEpics(_ context.Context, _, statusFilter string, limit, offset int32) ([]domain.EpicSummary, int32, error) {
	if f.listErr != nil {
		return nil, 0, f.listErr
	}
	src := f.epics
	if statusFilter != "" && statusFilter != "ALL" {
		filtered := make([]domain.EpicSummary, 0, len(src))
		for _, e := range src {
			if strings.EqualFold(e.Status, statusFilter) {
				filtered = append(filtered, e)
			}
		}
		src = filtered
	}
	total := int32(len(src))
	if limit <= 0 {
		return src, total, nil
	}
	start := int(offset)
	if start >= len(src) {
		return nil, total, nil
	}
	end := start + int(limit)
	if end > len(src) {
		end = len(src)
	}
	return src[start:end], total, nil
}

func (f *fakeFleetClient) ListStories(_ context.Context, _ string, _ string, limit, offset int32) ([]domain.StorySummary, int32, error) {
	if f.listErr != nil {
		return nil, 0, f.listErr
	}
	total := int32(len(f.stories))
	if limit <= 0 {
		return f.stories, total, nil
	}
	start := int(offset)
	if start >= len(f.stories) {
		return nil, total, nil
	}
	end := start + int(limit)
	if end > len(f.stories) {
		end = len(f.stories)
	}
	return f.stories[start:end], total, nil
}

func (f *fakeFleetClient) ListTasks(_ context.Context, _ string, _ string, limit, offset int32) ([]domain.TaskSummary, int32, error) {
	if f.listErr != nil {
		return nil, 0, f.listErr
	}
	total := int32(len(f.tasks))
	if limit <= 0 {
		return f.tasks, total, nil
	}
	start := int(offset)
	if start >= len(f.tasks) {
		return nil, total, nil
	}
	end := start + int(limit)
	if end > len(f.tasks) {
		end = len(f.tasks)
	}
	return f.tasks[start:end], total, nil
}

func (f *fakeFleetClient) ListCeremonies(_ context.Context, _, _ string, limit, offset int32) ([]domain.CeremonyStatus, int32, error) {
	if f.listErr != nil {
		return nil, 0, f.listErr
	}
	total := int32(len(f.ceremonies))
	if limit <= 0 {
		return f.ceremonies, total, nil
	}
	start := int(offset)
	if start >= len(f.ceremonies) {
		return nil, total, nil
	}
	end := start + int(limit)
	if end > len(f.ceremonies) {
		end = len(f.ceremonies)
	}
	return f.ceremonies[start:end], total, nil
}

func (f *fakeFleetClient) GetCeremony(_ context.Context, instanceID string) (domain.CeremonyStatus, error) {
	for _, c := range f.ceremonies {
		if c.InstanceID == instanceID {
			return c, nil
		}
	}
	return domain.CeremonyStatus{}, fmt.Errorf("ceremony %q not found", instanceID)
}

func (f *fakeFleetClient) ApproveDecision(_ context.Context, _, _, _ string) error {
	return f.approveErr
}

func (f *fakeFleetClient) RejectDecision(_ context.Context, _, _, _ string) error {
	return f.rejectErr
}

func (f *fakeFleetClient) WatchEvents(_ context.Context, _ []string, _ string) (<-chan domain.FleetEvent, error) {
	if f.events == nil {
		f.events = make(chan domain.FleetEvent, 8)
	}
	return f.events, nil
}

func (f *fakeFleetClient) CreateBacklogReview(_ context.Context, _ string, _ []string) (domain.BacklogReview, error) {
	return domain.BacklogReview{}, fmt.Errorf("not implemented")
}

func (f *fakeFleetClient) StartBacklogReview(_ context.Context, _, _ string) (domain.BacklogReview, int32, error) {
	return domain.BacklogReview{}, 0, fmt.Errorf("not implemented")
}

func (f *fakeFleetClient) GetBacklogReview(_ context.Context, ceremonyID string) (domain.BacklogReview, error) {
	if f.backlogReview != nil {
		return *f.backlogReview, nil
	}
	for _, r := range f.backlogReviews {
		if r.CeremonyID == ceremonyID {
			return r, nil
		}
	}
	return domain.BacklogReview{}, fmt.Errorf("backlog review %q not found", ceremonyID)
}

func (f *fakeFleetClient) ListBacklogReviews(_ context.Context, _ string, _, _ int32) ([]domain.BacklogReview, int32, error) {
	if f.listErr != nil {
		return nil, 0, f.listErr
	}
	return f.backlogReviews, int32(len(f.backlogReviews)), nil
}

func (f *fakeFleetClient) ApproveReviewPlan(_ context.Context, _, _, _, _, _, _, _ string) (domain.BacklogReview, string, error) {
	return domain.BacklogReview{}, "", fmt.Errorf("not implemented")
}

func (f *fakeFleetClient) RejectReviewPlan(_ context.Context, _, _, _, _ string) (domain.BacklogReview, error) {
	return domain.BacklogReview{}, fmt.Errorf("not implemented")
}

func (f *fakeFleetClient) CompleteBacklogReview(_ context.Context, _, _ string) (domain.BacklogReview, error) {
	return domain.BacklogReview{}, fmt.Errorf("not implemented")
}

func (f *fakeFleetClient) CancelBacklogReview(_ context.Context, _, _ string) (domain.BacklogReview, error) {
	return domain.BacklogReview{}, fmt.Errorf("not implemented")
}

func (f *fakeFleetClient) Close() error { return nil }
