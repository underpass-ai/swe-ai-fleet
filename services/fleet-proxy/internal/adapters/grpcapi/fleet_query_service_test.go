package grpcapi

import (
	"context"
	"errors"
	"testing"
	"time"

	proxyv1 "github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/gen/proxyv1"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/query"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/event"
)

// ---------------------------------------------------------------------------
// Helpers: construct a FleetQueryService with all handlers
// ---------------------------------------------------------------------------

func newTestQueryService(p ports.PlanningClient, c ports.CeremonyClient, es ports.EventSubscriber) *FleetQueryService {
	return NewFleetQueryService(QueryHandlers{
		ListProjects:       query.NewListProjectsHandler(p),
		ListEpics:          query.NewListEpicsHandler(p),
		ListStories:        query.NewListStoriesHandler(p),
		ListTasks:          query.NewListTasksHandler(p),
		GetCeremony:        query.NewGetCeremonyHandler(c),
		ListCeremonies:     query.NewListCeremoniesHandler(c),
		WatchEvents:        query.NewWatchEventsHandler(es),
		GetBacklogReview:   query.NewGetBacklogReviewHandler(p),
		ListBacklogReviews: query.NewListBacklogReviewsHandler(p),
	})
}

// ---------------------------------------------------------------------------
// ListProjects
// ---------------------------------------------------------------------------

func TestListProjects_Success(t *testing.T) {
	p := &fakePlanningClientCmd{
		projects: []ports.ProjectResult{
			{
				ProjectID:   "proj-1",
				Name:        "Alpha",
				Description: "Alpha project",
				Status:      "active",
				Owner:       "user-1",
				CreatedAt:   "2024-01-01T00:00:00Z",
				UpdatedAt:   "2024-01-02T00:00:00Z",
			},
			{
				ProjectID:   "proj-2",
				Name:        "Beta",
				Description: "Beta project",
				Status:      "archived",
				Owner:       "user-2",
				CreatedAt:   "2024-02-01T00:00:00Z",
				UpdatedAt:   "2024-02-02T00:00:00Z",
			},
		},
		projectTotal: 2,
	}
	svc := newTestQueryService(p, &fakeCeremonyClientCmd{}, &fakeEventSubscriberGRPC{})

	resp, err := svc.ListProjects(context.Background(), &proxyv1.ListProjectsRequest{
		StatusFilter: "active",
		Limit:        10,
		Offset:       0,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if resp.TotalCount != 2 {
		t.Errorf("TotalCount = %d, want 2", resp.TotalCount)
	}
	if len(resp.Projects) != 2 {
		t.Fatalf("Projects len = %d, want 2", len(resp.Projects))
	}

	proj := resp.Projects[0]
	if proj.ProjectId != "proj-1" {
		t.Errorf("ProjectId = %q, want %q", proj.ProjectId, "proj-1")
	}
	if proj.Name != "Alpha" {
		t.Errorf("Name = %q, want %q", proj.Name, "Alpha")
	}
	if proj.Description != "Alpha project" {
		t.Errorf("Description = %q, want %q", proj.Description, "Alpha project")
	}
	if proj.Status != "active" {
		t.Errorf("Status = %q, want %q", proj.Status, "active")
	}
	if proj.Owner != "user-1" {
		t.Errorf("Owner = %q, want %q", proj.Owner, "user-1")
	}
	if proj.CreatedAt != "2024-01-01T00:00:00Z" {
		t.Errorf("CreatedAt = %q, want %q", proj.CreatedAt, "2024-01-01T00:00:00Z")
	}
	if proj.UpdatedAt != "2024-01-02T00:00:00Z" {
		t.Errorf("UpdatedAt = %q, want %q", proj.UpdatedAt, "2024-01-02T00:00:00Z")
	}
}

func TestListProjects_HandlerError(t *testing.T) {
	p := &fakePlanningClientCmd{projectErr: errors.New("boom")}
	svc := newTestQueryService(p, &fakeCeremonyClientCmd{}, &fakeEventSubscriberGRPC{})

	_, err := svc.ListProjects(context.Background(), &proxyv1.ListProjectsRequest{})
	if err == nil {
		t.Fatal("expected error")
	}
}

func TestListProjects_Empty(t *testing.T) {
	p := &fakePlanningClientCmd{}
	svc := newTestQueryService(p, &fakeCeremonyClientCmd{}, &fakeEventSubscriberGRPC{})

	resp, err := svc.ListProjects(context.Background(), &proxyv1.ListProjectsRequest{})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(resp.Projects) != 0 {
		t.Errorf("Projects len = %d, want 0", len(resp.Projects))
	}
}

// ---------------------------------------------------------------------------
// ListEpics
// ---------------------------------------------------------------------------

func TestListEpics_Success(t *testing.T) {
	p := &fakePlanningClientCmd{
		epics: []ports.EpicResult{
			{
				EpicID:      "epic-1",
				ProjectID:   "proj-1",
				Title:       "Epic One",
				Description: "desc",
				Status:      "open",
				CreatedAt:   "2024-01-01T00:00:00Z",
				UpdatedAt:   "2024-01-02T00:00:00Z",
			},
		},
		epicTotal: 1,
	}
	svc := newTestQueryService(p, &fakeCeremonyClientCmd{}, &fakeEventSubscriberGRPC{})

	resp, err := svc.ListEpics(context.Background(), &proxyv1.ListEpicsRequest{
		ProjectId:    "proj-1",
		StatusFilter: "open",
		Limit:        10,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if resp.TotalCount != 1 {
		t.Errorf("TotalCount = %d, want 1", resp.TotalCount)
	}
	if len(resp.Epics) != 1 {
		t.Fatalf("Epics len = %d, want 1", len(resp.Epics))
	}

	e := resp.Epics[0]
	if e.EpicId != "epic-1" {
		t.Errorf("EpicId = %q, want %q", e.EpicId, "epic-1")
	}
	if e.ProjectId != "proj-1" {
		t.Errorf("ProjectId = %q, want %q", e.ProjectId, "proj-1")
	}
	if e.Title != "Epic One" {
		t.Errorf("Title = %q, want %q", e.Title, "Epic One")
	}
	if e.Description != "desc" {
		t.Errorf("Description = %q, want %q", e.Description, "desc")
	}
	if e.Status != "open" {
		t.Errorf("Status = %q, want %q", e.Status, "open")
	}
	if e.CreatedAt != "2024-01-01T00:00:00Z" {
		t.Errorf("CreatedAt = %q, want %q", e.CreatedAt, "2024-01-01T00:00:00Z")
	}
	if e.UpdatedAt != "2024-01-02T00:00:00Z" {
		t.Errorf("UpdatedAt = %q, want %q", e.UpdatedAt, "2024-01-02T00:00:00Z")
	}
}

func TestListEpics_HandlerError(t *testing.T) {
	p := &fakePlanningClientCmd{epicErr: errors.New("boom")}
	svc := newTestQueryService(p, &fakeCeremonyClientCmd{}, &fakeEventSubscriberGRPC{})

	_, err := svc.ListEpics(context.Background(), &proxyv1.ListEpicsRequest{
		ProjectId: "proj-1",
	})
	if err == nil {
		t.Fatal("expected error")
	}
}

func TestListEpics_ValidationError(t *testing.T) {
	svc := newTestQueryService(&fakePlanningClientCmd{}, &fakeCeremonyClientCmd{}, &fakeEventSubscriberGRPC{})
	// missing ProjectId
	_, err := svc.ListEpics(context.Background(), &proxyv1.ListEpicsRequest{})
	if err == nil {
		t.Fatal("expected error for missing project_id")
	}
}

// ---------------------------------------------------------------------------
// ListStories
// ---------------------------------------------------------------------------

func TestListStories_Success(t *testing.T) {
	p := &fakePlanningClientCmd{
		stories: []ports.StoryResult{
			{
				StoryID:   "story-1",
				EpicID:    "epic-1",
				Title:     "Story One",
				Brief:     "brief",
				State:     "draft",
				DorScore:  3,
				CreatedBy: "user-1",
				CreatedAt: "2024-01-01T00:00:00Z",
				UpdatedAt: "2024-01-02T00:00:00Z",
			},
		},
		storyTotal: 1,
	}
	svc := newTestQueryService(p, &fakeCeremonyClientCmd{}, &fakeEventSubscriberGRPC{})

	resp, err := svc.ListStories(context.Background(), &proxyv1.ListStoriesRequest{
		EpicId:      "epic-1",
		StateFilter: "draft",
		Limit:       10,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if resp.TotalCount != 1 {
		t.Errorf("TotalCount = %d, want 1", resp.TotalCount)
	}
	if len(resp.Stories) != 1 {
		t.Fatalf("Stories len = %d, want 1", len(resp.Stories))
	}

	s := resp.Stories[0]
	if s.StoryId != "story-1" {
		t.Errorf("StoryId = %q, want %q", s.StoryId, "story-1")
	}
	if s.EpicId != "epic-1" {
		t.Errorf("EpicId = %q, want %q", s.EpicId, "epic-1")
	}
	if s.Title != "Story One" {
		t.Errorf("Title = %q, want %q", s.Title, "Story One")
	}
	if s.Brief != "brief" {
		t.Errorf("Brief = %q, want %q", s.Brief, "brief")
	}
	if s.State != "draft" {
		t.Errorf("State = %q, want %q", s.State, "draft")
	}
	if s.DorScore != 3 {
		t.Errorf("DorScore = %d, want 3", s.DorScore)
	}
	if s.CreatedBy != "user-1" {
		t.Errorf("CreatedBy = %q, want %q", s.CreatedBy, "user-1")
	}
	if s.CreatedAt != "2024-01-01T00:00:00Z" {
		t.Errorf("CreatedAt = %q, want %q", s.CreatedAt, "2024-01-01T00:00:00Z")
	}
	if s.UpdatedAt != "2024-01-02T00:00:00Z" {
		t.Errorf("UpdatedAt = %q, want %q", s.UpdatedAt, "2024-01-02T00:00:00Z")
	}
}

func TestListStories_HandlerError(t *testing.T) {
	p := &fakePlanningClientCmd{storyErr: errors.New("boom")}
	svc := newTestQueryService(p, &fakeCeremonyClientCmd{}, &fakeEventSubscriberGRPC{})

	_, err := svc.ListStories(context.Background(), &proxyv1.ListStoriesRequest{
		EpicId: "epic-1",
	})
	if err == nil {
		t.Fatal("expected error")
	}
}

func TestListStories_ValidationError(t *testing.T) {
	svc := newTestQueryService(&fakePlanningClientCmd{}, &fakeCeremonyClientCmd{}, &fakeEventSubscriberGRPC{})
	// missing EpicId
	_, err := svc.ListStories(context.Background(), &proxyv1.ListStoriesRequest{})
	if err == nil {
		t.Fatal("expected error for missing epic_id")
	}
}

// ---------------------------------------------------------------------------
// ListTasks
// ---------------------------------------------------------------------------

func TestListTasks_Success(t *testing.T) {
	p := &fakePlanningClientCmd{
		tasks: []ports.TaskResult{
			{
				TaskID:         "task-1",
				StoryID:        "story-1",
				Title:          "Task One",
				Description:    "desc",
				Type:           "dev",
				Status:         "open",
				AssignedTo:     "agent-1",
				EstimatedHours: 4,
				Priority:       1,
				CreatedAt:      "2024-01-01T00:00:00Z",
				UpdatedAt:      "2024-01-02T00:00:00Z",
			},
		},
		taskTotal: 1,
	}
	svc := newTestQueryService(p, &fakeCeremonyClientCmd{}, &fakeEventSubscriberGRPC{})

	resp, err := svc.ListTasks(context.Background(), &proxyv1.ListTasksRequest{
		StoryId:      "story-1",
		StatusFilter: "open",
		Limit:        10,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if resp.TotalCount != 1 {
		t.Errorf("TotalCount = %d, want 1", resp.TotalCount)
	}
	if len(resp.Tasks) != 1 {
		t.Fatalf("Tasks len = %d, want 1", len(resp.Tasks))
	}

	tk := resp.Tasks[0]
	if tk.TaskId != "task-1" {
		t.Errorf("TaskId = %q, want %q", tk.TaskId, "task-1")
	}
	if tk.StoryId != "story-1" {
		t.Errorf("StoryId = %q, want %q", tk.StoryId, "story-1")
	}
	if tk.Title != "Task One" {
		t.Errorf("Title = %q, want %q", tk.Title, "Task One")
	}
	if tk.Description != "desc" {
		t.Errorf("Description = %q, want %q", tk.Description, "desc")
	}
	if tk.Type != "dev" {
		t.Errorf("Type = %q, want %q", tk.Type, "dev")
	}
	if tk.Status != "open" {
		t.Errorf("Status = %q, want %q", tk.Status, "open")
	}
	if tk.AssignedTo != "agent-1" {
		t.Errorf("AssignedTo = %q, want %q", tk.AssignedTo, "agent-1")
	}
	if tk.EstimatedHours != 4 {
		t.Errorf("EstimatedHours = %d, want 4", tk.EstimatedHours)
	}
	if tk.Priority != 1 {
		t.Errorf("Priority = %d, want 1", tk.Priority)
	}
	if tk.CreatedAt != "2024-01-01T00:00:00Z" {
		t.Errorf("CreatedAt = %q, want %q", tk.CreatedAt, "2024-01-01T00:00:00Z")
	}
	if tk.UpdatedAt != "2024-01-02T00:00:00Z" {
		t.Errorf("UpdatedAt = %q, want %q", tk.UpdatedAt, "2024-01-02T00:00:00Z")
	}
}

func TestListTasks_HandlerError(t *testing.T) {
	p := &fakePlanningClientCmd{taskErr: errors.New("boom")}
	svc := newTestQueryService(p, &fakeCeremonyClientCmd{}, &fakeEventSubscriberGRPC{})

	_, err := svc.ListTasks(context.Background(), &proxyv1.ListTasksRequest{
		StoryId: "story-1",
	})
	if err == nil {
		t.Fatal("expected error")
	}
}

func TestListTasks_ValidationError(t *testing.T) {
	svc := newTestQueryService(&fakePlanningClientCmd{}, &fakeCeremonyClientCmd{}, &fakeEventSubscriberGRPC{})
	// missing StoryId
	_, err := svc.ListTasks(context.Background(), &proxyv1.ListTasksRequest{})
	if err == nil {
		t.Fatal("expected error for missing story_id")
	}
}

// ---------------------------------------------------------------------------
// GetCeremonyInstance
// ---------------------------------------------------------------------------

func TestGetCeremonyInstance_Success(t *testing.T) {
	c := &fakeCeremonyClientCmd{
		getCeremony: ports.CeremonyResult{
			InstanceID:     "inst-1",
			CeremonyID:     "cer-1",
			StoryID:        "story-1",
			DefinitionName: "sprint_planning",
			CurrentState:   "running",
			Status:         "active",
			CorrelationID:  "corr-1",
			StepStatuses:   map[string]string{"step-1": "done", "step-2": "pending"},
			StepOutputs:    map[string]string{"step-1": "output-1"},
			CreatedAt:      "2024-01-01T00:00:00Z",
			UpdatedAt:      "2024-01-02T00:00:00Z",
		},
	}
	svc := newTestQueryService(&fakePlanningClientCmd{}, c, &fakeEventSubscriberGRPC{})

	resp, err := svc.GetCeremonyInstance(context.Background(), &proxyv1.GetCeremonyInstanceRequest{
		InstanceId: "inst-1",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if resp.Ceremony == nil {
		t.Fatal("Ceremony should not be nil")
	}

	cer := resp.Ceremony
	if cer.InstanceId != "inst-1" {
		t.Errorf("InstanceId = %q, want %q", cer.InstanceId, "inst-1")
	}
	if cer.CeremonyId != "cer-1" {
		t.Errorf("CeremonyId = %q, want %q", cer.CeremonyId, "cer-1")
	}
	if cer.StoryId != "story-1" {
		t.Errorf("StoryId = %q, want %q", cer.StoryId, "story-1")
	}
	if cer.DefinitionName != "sprint_planning" {
		t.Errorf("DefinitionName = %q, want %q", cer.DefinitionName, "sprint_planning")
	}
	if cer.CurrentState != "running" {
		t.Errorf("CurrentState = %q, want %q", cer.CurrentState, "running")
	}
	if cer.Status != "active" {
		t.Errorf("Status = %q, want %q", cer.Status, "active")
	}
	if cer.CorrelationId != "corr-1" {
		t.Errorf("CorrelationId = %q, want %q", cer.CorrelationId, "corr-1")
	}
	if len(cer.StepStatus) != 2 {
		t.Errorf("StepStatus len = %d, want 2", len(cer.StepStatus))
	}
	if cer.StepStatus["step-1"] != "done" {
		t.Errorf("StepStatus[step-1] = %q, want %q", cer.StepStatus["step-1"], "done")
	}
	if len(cer.StepOutputs) != 1 {
		t.Errorf("StepOutputs len = %d, want 1", len(cer.StepOutputs))
	}
	if cer.StepOutputs["step-1"] != "output-1" {
		t.Errorf("StepOutputs[step-1] = %q, want %q", cer.StepOutputs["step-1"], "output-1")
	}
	if cer.CreatedAt != "2024-01-01T00:00:00Z" {
		t.Errorf("CreatedAt = %q, want %q", cer.CreatedAt, "2024-01-01T00:00:00Z")
	}
	if cer.UpdatedAt != "2024-01-02T00:00:00Z" {
		t.Errorf("UpdatedAt = %q, want %q", cer.UpdatedAt, "2024-01-02T00:00:00Z")
	}
}

func TestGetCeremonyInstance_HandlerError(t *testing.T) {
	c := &fakeCeremonyClientCmd{getCeremonyErr: errors.New("not found")}
	svc := newTestQueryService(&fakePlanningClientCmd{}, c, &fakeEventSubscriberGRPC{})

	_, err := svc.GetCeremonyInstance(context.Background(), &proxyv1.GetCeremonyInstanceRequest{
		InstanceId: "inst-1",
	})
	if err == nil {
		t.Fatal("expected error")
	}
}

func TestGetCeremonyInstance_ValidationError(t *testing.T) {
	svc := newTestQueryService(&fakePlanningClientCmd{}, &fakeCeremonyClientCmd{}, &fakeEventSubscriberGRPC{})
	// missing InstanceId
	_, err := svc.GetCeremonyInstance(context.Background(), &proxyv1.GetCeremonyInstanceRequest{})
	if err == nil {
		t.Fatal("expected error for missing instance_id")
	}
}

// ---------------------------------------------------------------------------
// ListCeremonyInstances
// ---------------------------------------------------------------------------

func TestListCeremonyInstances_Success(t *testing.T) {
	c := &fakeCeremonyClientCmd{
		ceremonies: []ports.CeremonyResult{
			{
				InstanceID:     "inst-1",
				CeremonyID:     "cer-1",
				DefinitionName: "sprint_planning",
				Status:         "completed",
				CreatedAt:      "2024-01-01T00:00:00Z",
				UpdatedAt:      "2024-01-02T00:00:00Z",
			},
			{
				InstanceID:     "inst-2",
				CeremonyID:     "cer-1",
				DefinitionName: "sprint_planning",
				Status:         "active",
				CreatedAt:      "2024-02-01T00:00:00Z",
				UpdatedAt:      "2024-02-02T00:00:00Z",
			},
		},
		ceremonyList: 2,
	}
	svc := newTestQueryService(&fakePlanningClientCmd{}, c, &fakeEventSubscriberGRPC{})

	resp, err := svc.ListCeremonyInstances(context.Background(), &proxyv1.ListCeremonyInstancesRequest{
		StoryId:     "story-1",
		StateFilter: "completed",
		Limit:       10,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if resp.TotalCount != 2 {
		t.Errorf("TotalCount = %d, want 2", resp.TotalCount)
	}
	if len(resp.Ceremonies) != 2 {
		t.Fatalf("Ceremonies len = %d, want 2", len(resp.Ceremonies))
	}
	if resp.Ceremonies[0].InstanceId != "inst-1" {
		t.Errorf("Ceremonies[0].InstanceId = %q, want %q", resp.Ceremonies[0].InstanceId, "inst-1")
	}
	if resp.Ceremonies[1].InstanceId != "inst-2" {
		t.Errorf("Ceremonies[1].InstanceId = %q, want %q", resp.Ceremonies[1].InstanceId, "inst-2")
	}
}

func TestListCeremonyInstances_HandlerError(t *testing.T) {
	c := &fakeCeremonyClientCmd{listErr: errors.New("boom")}
	svc := newTestQueryService(&fakePlanningClientCmd{}, c, &fakeEventSubscriberGRPC{})

	_, err := svc.ListCeremonyInstances(context.Background(), &proxyv1.ListCeremonyInstancesRequest{})
	if err == nil {
		t.Fatal("expected error")
	}
}

// ---------------------------------------------------------------------------
// GetBacklogReview
// ---------------------------------------------------------------------------

func TestGetBacklogReview_Success(t *testing.T) {
	p := &fakePlanningClientCmd{
		getBacklogResult: ports.BacklogReviewResult{
			CeremonyID: "cer-1",
			Status:     "in_progress",
			StoryIDs:   []string{"s1"},
			CreatedBy:  "user-1",
			CreatedAt:  "2024-01-01T00:00:00Z",
			UpdatedAt:  "2024-01-02T00:00:00Z",
		},
	}
	svc := newTestQueryService(p, &fakeCeremonyClientCmd{}, &fakeEventSubscriberGRPC{})

	resp, err := svc.GetBacklogReview(context.Background(), &proxyv1.GetBacklogReviewRequest{
		CeremonyId: "cer-1",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !resp.Success {
		t.Error("Success should be true")
	}
	if resp.Message != "backlog review retrieved" {
		t.Errorf("Message = %q, want %q", resp.Message, "backlog review retrieved")
	}
	if resp.Ceremony == nil {
		t.Fatal("Ceremony should not be nil")
	}
	if resp.Ceremony.CeremonyId != "cer-1" {
		t.Errorf("Ceremony.CeremonyId = %q, want %q", resp.Ceremony.CeremonyId, "cer-1")
	}
	if resp.Ceremony.Status != "in_progress" {
		t.Errorf("Ceremony.Status = %q, want %q", resp.Ceremony.Status, "in_progress")
	}
	if resp.Ceremony.CreatedBy != "user-1" {
		t.Errorf("Ceremony.CreatedBy = %q, want %q", resp.Ceremony.CreatedBy, "user-1")
	}
}

func TestGetBacklogReview_HandlerError(t *testing.T) {
	p := &fakePlanningClientCmd{getBacklogErr: errors.New("not found")}
	svc := newTestQueryService(p, &fakeCeremonyClientCmd{}, &fakeEventSubscriberGRPC{})

	_, err := svc.GetBacklogReview(context.Background(), &proxyv1.GetBacklogReviewRequest{
		CeremonyId: "cer-1",
	})
	if err == nil {
		t.Fatal("expected error")
	}
}

func TestGetBacklogReview_ValidationError(t *testing.T) {
	svc := newTestQueryService(&fakePlanningClientCmd{}, &fakeCeremonyClientCmd{}, &fakeEventSubscriberGRPC{})
	// missing CeremonyId
	_, err := svc.GetBacklogReview(context.Background(), &proxyv1.GetBacklogReviewRequest{})
	if err == nil {
		t.Fatal("expected error for missing ceremony_id")
	}
}

// ---------------------------------------------------------------------------
// ListBacklogReviews
// ---------------------------------------------------------------------------

func TestListBacklogReviews_Success(t *testing.T) {
	p := &fakePlanningClientCmd{
		listBacklogResults: []ports.BacklogReviewResult{
			{CeremonyID: "cer-1", Status: "completed"},
			{CeremonyID: "cer-2", Status: "in_progress"},
		},
		listBacklogTotal: 2,
	}
	svc := newTestQueryService(p, &fakeCeremonyClientCmd{}, &fakeEventSubscriberGRPC{})

	resp, err := svc.ListBacklogReviews(context.Background(), &proxyv1.ListBacklogReviewsRequest{
		StatusFilter: "completed",
		Limit:        10,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if resp.TotalCount != 2 {
		t.Errorf("TotalCount = %d, want 2", resp.TotalCount)
	}
	if len(resp.Ceremonies) != 2 {
		t.Fatalf("Ceremonies len = %d, want 2", len(resp.Ceremonies))
	}
	if resp.Ceremonies[0].CeremonyId != "cer-1" {
		t.Errorf("Ceremonies[0].CeremonyId = %q, want %q", resp.Ceremonies[0].CeremonyId, "cer-1")
	}
	if resp.Ceremonies[1].CeremonyId != "cer-2" {
		t.Errorf("Ceremonies[1].CeremonyId = %q, want %q", resp.Ceremonies[1].CeremonyId, "cer-2")
	}
}

func TestListBacklogReviews_HandlerError(t *testing.T) {
	p := &fakePlanningClientCmd{listBacklogErr: errors.New("boom")}
	svc := newTestQueryService(p, &fakeCeremonyClientCmd{}, &fakeEventSubscriberGRPC{})

	_, err := svc.ListBacklogReviews(context.Background(), &proxyv1.ListBacklogReviewsRequest{})
	if err == nil {
		t.Fatal("expected error")
	}
}

// ---------------------------------------------------------------------------
// WatchEvents — stream-based tests
// ---------------------------------------------------------------------------

func TestWatchEvents_ChannelClose(t *testing.T) {
	ch := make(chan event.FleetEvent)
	es := &fakeEventSubscriberGRPC{ch: ch}
	svc := newTestQueryService(&fakePlanningClientCmd{}, &fakeCeremonyClientCmd{}, es)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	stream := &fakeWatchStream{ctx: ctx}

	// Close the channel immediately to simulate subscriber shutdown.
	close(ch)

	err := svc.WatchEvents(&proxyv1.WatchEventsRequest{}, stream)
	// Channel close should return nil (graceful end).
	if err != nil {
		t.Fatalf("expected nil error on channel close, got: %v", err)
	}
}

func TestWatchEvents_SendsEvent(t *testing.T) {
	ch := make(chan event.FleetEvent, 1)
	es := &fakeEventSubscriberGRPC{ch: ch}
	svc := newTestQueryService(&fakePlanningClientCmd{}, &fakeCeremonyClientCmd{}, es)

	ctx, cancel := context.WithCancel(context.Background())
	stream := &fakeWatchStream{ctx: ctx}

	ts := time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC)
	ch <- event.FleetEvent{
		Type:           event.EventStoryCreated,
		IdempotencyKey: "idem-1",
		CorrelationID:  "corr-1",
		Timestamp:      ts,
		Producer:       "test-producer",
		Payload:        []byte(`{"story_id":"s1"}`),
	}

	// Close channel after sending one event so the loop terminates.
	close(ch)

	err := svc.WatchEvents(&proxyv1.WatchEventsRequest{}, stream)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	cancel()

	if len(stream.sent) != 1 {
		t.Fatalf("sent len = %d, want 1", len(stream.sent))
	}

	msg := stream.sent[0]
	if msg.EventType != "story.created" {
		t.Errorf("EventType = %q, want %q", msg.EventType, "story.created")
	}
	if msg.IdempotencyKey != "idem-1" {
		t.Errorf("IdempotencyKey = %q, want %q", msg.IdempotencyKey, "idem-1")
	}
	if msg.CorrelationId != "corr-1" {
		t.Errorf("CorrelationId = %q, want %q", msg.CorrelationId, "corr-1")
	}
	if msg.Producer != "test-producer" {
		t.Errorf("Producer = %q, want %q", msg.Producer, "test-producer")
	}
	if string(msg.Payload) != `{"story_id":"s1"}` {
		t.Errorf("Payload = %q, want %q", string(msg.Payload), `{"story_id":"s1"}`)
	}
	expectedTS := ts.Format("2006-01-02T15:04:05Z07:00")
	if msg.Timestamp != expectedTS {
		t.Errorf("Timestamp = %q, want %q", msg.Timestamp, expectedTS)
	}
}

func TestWatchEvents_SendError(t *testing.T) {
	ch := make(chan event.FleetEvent, 1)
	es := &fakeEventSubscriberGRPC{ch: ch}
	svc := newTestQueryService(&fakePlanningClientCmd{}, &fakeCeremonyClientCmd{}, es)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	stream := &fakeWatchStream{
		ctx:     ctx,
		sendErr: errors.New("stream broken"),
	}

	ch <- event.FleetEvent{
		Type:           event.EventStoryCreated,
		IdempotencyKey: "idem-1",
		CorrelationID:  "corr-1",
		Producer:       "producer",
		Timestamp:      time.Now(),
	}

	err := svc.WatchEvents(&proxyv1.WatchEventsRequest{}, stream)
	if err == nil {
		t.Fatal("expected error from Send failure")
	}
}

func TestWatchEvents_SubscribeError(t *testing.T) {
	es := &fakeEventSubscriberGRPC{err: errors.New("subscribe failed")}
	svc := newTestQueryService(&fakePlanningClientCmd{}, &fakeCeremonyClientCmd{}, es)

	ctx := context.Background()
	stream := &fakeWatchStream{ctx: ctx}

	err := svc.WatchEvents(&proxyv1.WatchEventsRequest{}, stream)
	if err == nil {
		t.Fatal("expected error from subscribe failure")
	}
}

func TestWatchEvents_InvalidEventType(t *testing.T) {
	es := &fakeEventSubscriberGRPC{}
	svc := newTestQueryService(&fakePlanningClientCmd{}, &fakeCeremonyClientCmd{}, es)

	ctx := context.Background()
	stream := &fakeWatchStream{ctx: ctx}

	err := svc.WatchEvents(&proxyv1.WatchEventsRequest{
		EventTypes: []string{"invalid.type"},
	}, stream)
	if err == nil {
		t.Fatal("expected error for invalid event type")
	}
}

func TestWatchEvents_WithEventTypeFilter(t *testing.T) {
	ch := make(chan event.FleetEvent)
	es := &fakeEventSubscriberGRPC{ch: ch}
	svc := newTestQueryService(&fakePlanningClientCmd{}, &fakeCeremonyClientCmd{}, es)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	stream := &fakeWatchStream{ctx: ctx}

	close(ch)

	err := svc.WatchEvents(&proxyv1.WatchEventsRequest{
		EventTypes: []string{"story.created"},
	}, stream)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestWatchEvents_WithProjectIDFilter(t *testing.T) {
	ch := make(chan event.FleetEvent)
	es := &fakeEventSubscriberGRPC{ch: ch}
	svc := newTestQueryService(&fakePlanningClientCmd{}, &fakeCeremonyClientCmd{}, es)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	stream := &fakeWatchStream{ctx: ctx}

	close(ch)

	err := svc.WatchEvents(&proxyv1.WatchEventsRequest{
		ProjectId: "proj-1",
	}, stream)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestWatchEvents_ContextCancelled(t *testing.T) {
	ch := make(chan event.FleetEvent)
	es := &fakeEventSubscriberGRPC{ch: ch}
	svc := newTestQueryService(&fakePlanningClientCmd{}, &fakeCeremonyClientCmd{}, es)

	ctx, cancel := context.WithCancel(context.Background())
	stream := &fakeWatchStream{ctx: ctx}

	// Cancel the context before the goroutine enters the select.
	cancel()

	err := svc.WatchEvents(&proxyv1.WatchEventsRequest{}, stream)
	// Context cancellation returns a gRPC status error.
	if err == nil {
		t.Fatal("expected error from context cancellation")
	}
}

// ---------------------------------------------------------------------------
// Mapping helper tests (query service side)
// ---------------------------------------------------------------------------

func TestProjectResultToProto(t *testing.T) {
	p := ports.ProjectResult{
		ProjectID:   "proj-1",
		Name:        "name",
		Description: "desc",
		Status:      "active",
		Owner:       "owner",
		CreatedAt:   "created",
		UpdatedAt:   "updated",
	}

	proto := projectResultToProto(p)

	if proto.ProjectId != "proj-1" {
		t.Errorf("ProjectId = %q, want %q", proto.ProjectId, "proj-1")
	}
	if proto.Name != "name" {
		t.Errorf("Name = %q, want %q", proto.Name, "name")
	}
	if proto.Description != "desc" {
		t.Errorf("Description = %q, want %q", proto.Description, "desc")
	}
	if proto.Status != "active" {
		t.Errorf("Status = %q, want %q", proto.Status, "active")
	}
	if proto.Owner != "owner" {
		t.Errorf("Owner = %q, want %q", proto.Owner, "owner")
	}
	if proto.CreatedAt != "created" {
		t.Errorf("CreatedAt = %q, want %q", proto.CreatedAt, "created")
	}
	if proto.UpdatedAt != "updated" {
		t.Errorf("UpdatedAt = %q, want %q", proto.UpdatedAt, "updated")
	}
}

func TestEpicResultToProto(t *testing.T) {
	e := ports.EpicResult{
		EpicID:      "epic-1",
		ProjectID:   "proj-1",
		Title:       "title",
		Description: "desc",
		Status:      "open",
		CreatedAt:   "created",
		UpdatedAt:   "updated",
	}

	proto := epicResultToProto(e)

	if proto.EpicId != "epic-1" {
		t.Errorf("EpicId = %q, want %q", proto.EpicId, "epic-1")
	}
	if proto.ProjectId != "proj-1" {
		t.Errorf("ProjectId = %q, want %q", proto.ProjectId, "proj-1")
	}
	if proto.Title != "title" {
		t.Errorf("Title = %q, want %q", proto.Title, "title")
	}
	if proto.Description != "desc" {
		t.Errorf("Description = %q, want %q", proto.Description, "desc")
	}
	if proto.Status != "open" {
		t.Errorf("Status = %q, want %q", proto.Status, "open")
	}
}

func TestStoryResultToProto(t *testing.T) {
	s := ports.StoryResult{
		StoryID:   "story-1",
		EpicID:    "epic-1",
		Title:     "title",
		Brief:     "brief",
		State:     "draft",
		DorScore:  5,
		CreatedBy: "user",
		CreatedAt: "created",
		UpdatedAt: "updated",
	}

	proto := storyResultToProto(s)

	if proto.StoryId != "story-1" {
		t.Errorf("StoryId = %q, want %q", proto.StoryId, "story-1")
	}
	if proto.EpicId != "epic-1" {
		t.Errorf("EpicId = %q, want %q", proto.EpicId, "epic-1")
	}
	if proto.Title != "title" {
		t.Errorf("Title = %q, want %q", proto.Title, "title")
	}
	if proto.Brief != "brief" {
		t.Errorf("Brief = %q, want %q", proto.Brief, "brief")
	}
	if proto.State != "draft" {
		t.Errorf("State = %q, want %q", proto.State, "draft")
	}
	if proto.DorScore != 5 {
		t.Errorf("DorScore = %d, want 5", proto.DorScore)
	}
	if proto.CreatedBy != "user" {
		t.Errorf("CreatedBy = %q, want %q", proto.CreatedBy, "user")
	}
}

func TestTaskResultToProto(t *testing.T) {
	tk := ports.TaskResult{
		TaskID:         "task-1",
		StoryID:        "story-1",
		Title:          "title",
		Description:    "desc",
		Type:           "dev",
		Status:         "done",
		AssignedTo:     "agent",
		EstimatedHours: 8,
		Priority:       2,
		CreatedAt:      "created",
		UpdatedAt:      "updated",
	}

	proto := taskResultToProto(tk)

	if proto.TaskId != "task-1" {
		t.Errorf("TaskId = %q, want %q", proto.TaskId, "task-1")
	}
	if proto.StoryId != "story-1" {
		t.Errorf("StoryId = %q, want %q", proto.StoryId, "story-1")
	}
	if proto.Title != "title" {
		t.Errorf("Title = %q, want %q", proto.Title, "title")
	}
	if proto.Description != "desc" {
		t.Errorf("Description = %q, want %q", proto.Description, "desc")
	}
	if proto.Type != "dev" {
		t.Errorf("Type = %q, want %q", proto.Type, "dev")
	}
	if proto.Status != "done" {
		t.Errorf("Status = %q, want %q", proto.Status, "done")
	}
	if proto.AssignedTo != "agent" {
		t.Errorf("AssignedTo = %q, want %q", proto.AssignedTo, "agent")
	}
	if proto.EstimatedHours != 8 {
		t.Errorf("EstimatedHours = %d, want 8", proto.EstimatedHours)
	}
	if proto.Priority != 2 {
		t.Errorf("Priority = %d, want 2", proto.Priority)
	}
}

func TestCeremonyResultToProto(t *testing.T) {
	c := ports.CeremonyResult{
		InstanceID:     "inst-1",
		CeremonyID:     "cer-1",
		StoryID:        "story-1",
		DefinitionName: "def",
		CurrentState:   "running",
		Status:         "active",
		CorrelationID:  "corr-1",
		StepStatuses:   map[string]string{"s1": "done"},
		StepOutputs:    map[string]string{"s1": "out"},
		CreatedAt:      "created",
		UpdatedAt:      "updated",
	}

	proto := ceremonyResultToProto(c)

	if proto.InstanceId != "inst-1" {
		t.Errorf("InstanceId = %q, want %q", proto.InstanceId, "inst-1")
	}
	if proto.CeremonyId != "cer-1" {
		t.Errorf("CeremonyId = %q, want %q", proto.CeremonyId, "cer-1")
	}
	if proto.StoryId != "story-1" {
		t.Errorf("StoryId = %q, want %q", proto.StoryId, "story-1")
	}
	if proto.DefinitionName != "def" {
		t.Errorf("DefinitionName = %q, want %q", proto.DefinitionName, "def")
	}
	if proto.CurrentState != "running" {
		t.Errorf("CurrentState = %q, want %q", proto.CurrentState, "running")
	}
	if proto.Status != "active" {
		t.Errorf("Status = %q, want %q", proto.Status, "active")
	}
	if proto.CorrelationId != "corr-1" {
		t.Errorf("CorrelationId = %q, want %q", proto.CorrelationId, "corr-1")
	}
	if len(proto.StepStatus) != 1 || proto.StepStatus["s1"] != "done" {
		t.Errorf("StepStatus = %v, want {s1:done}", proto.StepStatus)
	}
	if len(proto.StepOutputs) != 1 || proto.StepOutputs["s1"] != "out" {
		t.Errorf("StepOutputs = %v, want {s1:out}", proto.StepOutputs)
	}
	if proto.CreatedAt != "created" {
		t.Errorf("CreatedAt = %q, want %q", proto.CreatedAt, "created")
	}
	if proto.UpdatedAt != "updated" {
		t.Errorf("UpdatedAt = %q, want %q", proto.UpdatedAt, "updated")
	}
}
