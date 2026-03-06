package grpcapi

import (
	"context"
	"errors"
	"testing"

	proxyv1 "github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/gen/proxyv1"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/adapters/grpcapi/interceptors"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/command"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

// ---------------------------------------------------------------------------
// Helpers: context with client ID
// ---------------------------------------------------------------------------

func ctxWithClientID(clientID string) context.Context {
	return context.WithValue(context.Background(), interceptors.ClientIDKey, clientID)
}

// ---------------------------------------------------------------------------
// Helpers: construct a FleetCommandService with all handlers
// ---------------------------------------------------------------------------

func newTestCommandService(p ports.PlanningClient, c ports.CeremonyClient) *FleetCommandService {
	audit := &fakeAuditLogger{}
	return NewFleetCommandService(CommandHandlers{
		CreateProject:         command.NewCreateProjectHandler(p, audit, nil),
		CreateEpic:            command.NewCreateEpicHandler(p, audit),
		CreateStory:           command.NewCreateStoryHandler(p, audit, nil),
		TransitionStory:       command.NewTransitionStoryHandler(p, audit),
		CreateTask:            command.NewCreateTaskHandler(p, audit),
		StartCeremony:         command.NewStartCeremonyHandler(c, audit),
		StartBacklogReview:    command.NewStartBacklogReviewHandler(p, audit),
		ApproveDecision:       command.NewApproveDecisionHandler(p, audit),
		RejectDecision:        command.NewRejectDecisionHandler(p, audit),
		CreateBacklogReview:   command.NewCreateBacklogReviewHandler(p, audit),
		ApproveReviewPlan:     command.NewApproveReviewPlanHandler(p, audit),
		RejectReviewPlan:      command.NewRejectReviewPlanHandler(p, audit),
		CompleteBacklogReview: command.NewCompleteBacklogReviewHandler(p, audit),
		CancelBacklogReview:   command.NewCancelBacklogReviewHandler(p, audit),
	})
}

// ---------------------------------------------------------------------------
// CreateProject
// ---------------------------------------------------------------------------

func TestCreateProject_Success(t *testing.T) {
	p := &fakePlanningClientCmd{createProjectID: "proj-1"}
	svc := newTestCommandService(p, &fakeCeremonyClientCmd{})

	resp, err := svc.CreateProject(ctxWithClientID("client-1"), &proxyv1.CreateProjectRequest{
		RequestId:   "req-1",
		Name:        "my project",
		Description: "desc",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if resp.ProjectId != "proj-1" {
		t.Errorf("ProjectId = %q, want %q", resp.ProjectId, "proj-1")
	}
	if !resp.Success {
		t.Error("Success should be true")
	}
	if resp.Message != "project created" {
		t.Errorf("Message = %q, want %q", resp.Message, "project created")
	}
}

func TestCreateProject_HandlerError(t *testing.T) {
	p := &fakePlanningClientCmd{createProjectErr: errors.New("boom")}
	svc := newTestCommandService(p, &fakeCeremonyClientCmd{})

	_, err := svc.CreateProject(ctxWithClientID("client-1"), &proxyv1.CreateProjectRequest{
		RequestId:   "req-1",
		Name:        "my project",
		Description: "desc",
	})
	if err == nil {
		t.Fatal("expected error")
	}
}

func TestCreateProject_ValidationError(t *testing.T) {
	p := &fakePlanningClientCmd{}
	svc := newTestCommandService(p, &fakeCeremonyClientCmd{})

	// missing Name
	_, err := svc.CreateProject(ctxWithClientID("client-1"), &proxyv1.CreateProjectRequest{
		RequestId: "req-1",
	})
	if err == nil {
		t.Fatal("expected error for missing name")
	}
}

// ---------------------------------------------------------------------------
// CreateEpic
// ---------------------------------------------------------------------------

func TestCreateEpic_Success(t *testing.T) {
	p := &fakePlanningClientCmd{createEpicID: "epic-1"}
	svc := newTestCommandService(p, &fakeCeremonyClientCmd{})

	resp, err := svc.CreateEpic(ctxWithClientID("client-1"), &proxyv1.CreateEpicRequest{
		RequestId:   "req-1",
		ProjectId:   "proj-1",
		Title:       "my epic",
		Description: "desc",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if resp.EpicId != "epic-1" {
		t.Errorf("EpicId = %q, want %q", resp.EpicId, "epic-1")
	}
	if !resp.Success {
		t.Error("Success should be true")
	}
	if resp.Message != "epic created" {
		t.Errorf("Message = %q, want %q", resp.Message, "epic created")
	}
}

func TestCreateEpic_HandlerError(t *testing.T) {
	p := &fakePlanningClientCmd{createEpicErr: errors.New("boom")}
	svc := newTestCommandService(p, &fakeCeremonyClientCmd{})

	_, err := svc.CreateEpic(ctxWithClientID("client-1"), &proxyv1.CreateEpicRequest{
		RequestId:   "req-1",
		ProjectId:   "proj-1",
		Title:       "epic",
		Description: "desc",
	})
	if err == nil {
		t.Fatal("expected error")
	}
}

func TestCreateEpic_ValidationError(t *testing.T) {
	svc := newTestCommandService(&fakePlanningClientCmd{}, &fakeCeremonyClientCmd{})
	// missing ProjectId
	_, err := svc.CreateEpic(ctxWithClientID("client-1"), &proxyv1.CreateEpicRequest{
		RequestId: "req-1",
		Title:     "epic",
	})
	if err == nil {
		t.Fatal("expected error for missing project_id")
	}
}

// ---------------------------------------------------------------------------
// CreateStory
// ---------------------------------------------------------------------------

func TestCreateStory_Success(t *testing.T) {
	p := &fakePlanningClientCmd{createStoryID: "story-1"}
	svc := newTestCommandService(p, &fakeCeremonyClientCmd{})

	resp, err := svc.CreateStory(ctxWithClientID("client-1"), &proxyv1.CreateStoryRequest{
		RequestId: "req-1",
		EpicId:    "epic-1",
		Title:     "my story",
		Brief:     "brief",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if resp.StoryId != "story-1" {
		t.Errorf("StoryId = %q, want %q", resp.StoryId, "story-1")
	}
	if !resp.Success {
		t.Error("Success should be true")
	}
	if resp.Message != "story created" {
		t.Errorf("Message = %q, want %q", resp.Message, "story created")
	}
}

func TestCreateStory_HandlerError(t *testing.T) {
	p := &fakePlanningClientCmd{createStoryErr: errors.New("boom")}
	svc := newTestCommandService(p, &fakeCeremonyClientCmd{})

	_, err := svc.CreateStory(ctxWithClientID("client-1"), &proxyv1.CreateStoryRequest{
		RequestId: "req-1",
		EpicId:    "epic-1",
		Title:     "story",
		Brief:     "brief",
	})
	if err == nil {
		t.Fatal("expected error")
	}
}

func TestCreateStory_ValidationError(t *testing.T) {
	svc := newTestCommandService(&fakePlanningClientCmd{}, &fakeCeremonyClientCmd{})
	// missing EpicId
	_, err := svc.CreateStory(ctxWithClientID("client-1"), &proxyv1.CreateStoryRequest{
		RequestId: "req-1",
		Title:     "story",
	})
	if err == nil {
		t.Fatal("expected error for missing epic_id")
	}
}

// ---------------------------------------------------------------------------
// TransitionStory
// ---------------------------------------------------------------------------

func TestTransitionStory_Success(t *testing.T) {
	svc := newTestCommandService(&fakePlanningClientCmd{}, &fakeCeremonyClientCmd{})

	resp, err := svc.TransitionStory(ctxWithClientID("client-1"), &proxyv1.TransitionStoryRequest{
		StoryId:     "story-1",
		TargetState: "in_progress",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !resp.Success {
		t.Error("Success should be true")
	}
	if resp.Message != "story transitioned" {
		t.Errorf("Message = %q, want %q", resp.Message, "story transitioned")
	}
}

func TestTransitionStory_HandlerError(t *testing.T) {
	p := &fakePlanningClientCmd{transitionStoryErr: errors.New("boom")}
	svc := newTestCommandService(p, &fakeCeremonyClientCmd{})

	_, err := svc.TransitionStory(ctxWithClientID("client-1"), &proxyv1.TransitionStoryRequest{
		StoryId:     "story-1",
		TargetState: "in_progress",
	})
	if err == nil {
		t.Fatal("expected error")
	}
}

func TestTransitionStory_ValidationError(t *testing.T) {
	svc := newTestCommandService(&fakePlanningClientCmd{}, &fakeCeremonyClientCmd{})
	// missing TargetState
	_, err := svc.TransitionStory(ctxWithClientID("client-1"), &proxyv1.TransitionStoryRequest{
		StoryId: "story-1",
	})
	if err == nil {
		t.Fatal("expected error for missing target_state")
	}
}

// ---------------------------------------------------------------------------
// CreateTask
// ---------------------------------------------------------------------------

func TestCreateTask_Success(t *testing.T) {
	p := &fakePlanningClientCmd{createTaskID: "task-1"}
	svc := newTestCommandService(p, &fakeCeremonyClientCmd{})

	resp, err := svc.CreateTask(ctxWithClientID("client-1"), &proxyv1.CreateTaskRequest{
		RequestId:      "req-1",
		StoryId:        "story-1",
		Title:          "my task",
		Description:    "desc",
		Type:           "dev",
		AssignedTo:     "agent-1",
		EstimatedHours: 4,
		Priority:       1,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if resp.TaskId != "task-1" {
		t.Errorf("TaskId = %q, want %q", resp.TaskId, "task-1")
	}
	if !resp.Success {
		t.Error("Success should be true")
	}
	if resp.Message != "task created" {
		t.Errorf("Message = %q, want %q", resp.Message, "task created")
	}
}

func TestCreateTask_HandlerError(t *testing.T) {
	p := &fakePlanningClientCmd{createTaskErr: errors.New("boom")}
	svc := newTestCommandService(p, &fakeCeremonyClientCmd{})

	_, err := svc.CreateTask(ctxWithClientID("client-1"), &proxyv1.CreateTaskRequest{
		RequestId: "req-1",
		StoryId:   "story-1",
		Title:     "task",
		Type:      "dev",
	})
	if err == nil {
		t.Fatal("expected error")
	}
}

func TestCreateTask_ValidationError(t *testing.T) {
	svc := newTestCommandService(&fakePlanningClientCmd{}, &fakeCeremonyClientCmd{})
	// missing Type
	_, err := svc.CreateTask(ctxWithClientID("client-1"), &proxyv1.CreateTaskRequest{
		RequestId: "req-1",
		StoryId:   "story-1",
		Title:     "task",
	})
	if err == nil {
		t.Fatal("expected error for missing type")
	}
}

// ---------------------------------------------------------------------------
// StartPlanningCeremony
// ---------------------------------------------------------------------------

func TestStartPlanningCeremony_Success(t *testing.T) {
	c := &fakeCeremonyClientCmd{startCeremonyID: "inst-1"}
	svc := newTestCommandService(&fakePlanningClientCmd{}, c)

	resp, err := svc.StartPlanningCeremony(ctxWithClientID("client-1"), &proxyv1.StartPlanningCeremonyRequest{
		RequestId:      "req-1",
		CeremonyId:     "cer-1",
		DefinitionName: "sprint_planning",
		StoryId:        "story-1",
		StepIds:        []string{"step-1", "step-2"},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if resp.InstanceId != "inst-1" {
		t.Errorf("InstanceId = %q, want %q", resp.InstanceId, "inst-1")
	}
	if resp.Status != "started" {
		t.Errorf("Status = %q, want %q", resp.Status, "started")
	}
	if resp.Message != "ceremony started" {
		t.Errorf("Message = %q, want %q", resp.Message, "ceremony started")
	}
}

func TestStartPlanningCeremony_HandlerError(t *testing.T) {
	c := &fakeCeremonyClientCmd{startCeremonyErr: errors.New("boom")}
	svc := newTestCommandService(&fakePlanningClientCmd{}, c)

	_, err := svc.StartPlanningCeremony(ctxWithClientID("client-1"), &proxyv1.StartPlanningCeremonyRequest{
		RequestId:      "req-1",
		CeremonyId:     "cer-1",
		DefinitionName: "sprint_planning",
		StoryId:        "story-1",
		StepIds:        []string{"step-1"},
	})
	if err == nil {
		t.Fatal("expected error")
	}
}

func TestStartPlanningCeremony_ValidationError(t *testing.T) {
	svc := newTestCommandService(&fakePlanningClientCmd{}, &fakeCeremonyClientCmd{})
	// missing StepIds
	_, err := svc.StartPlanningCeremony(ctxWithClientID("client-1"), &proxyv1.StartPlanningCeremonyRequest{
		RequestId:      "req-1",
		CeremonyId:     "cer-1",
		DefinitionName: "sprint_planning",
		StoryId:        "story-1",
	})
	if err == nil {
		t.Fatal("expected error for missing step_ids")
	}
}

// ---------------------------------------------------------------------------
// StartBacklogReview
// ---------------------------------------------------------------------------

func TestStartBacklogReview_Success(t *testing.T) {
	p := &fakePlanningClientCmd{
		startBacklogReviewResult: ports.BacklogReviewResult{
			CeremonyID: "cer-1",
			Status:     "in_progress",
			StoryIDs:   []string{"s1", "s2"},
		},
		startBacklogReviewCount: 5,
	}
	svc := newTestCommandService(p, &fakeCeremonyClientCmd{})

	resp, err := svc.StartBacklogReview(ctxWithClientID("client-1"), &proxyv1.StartBacklogReviewRequest{
		RequestId:  "req-1",
		CeremonyId: "cer-1",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !resp.Success {
		t.Error("Success should be true")
	}
	if resp.TotalDeliberationsSubmitted != 5 {
		t.Errorf("TotalDeliberationsSubmitted = %d, want 5", resp.TotalDeliberationsSubmitted)
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
	if resp.Message != "backlog review started" {
		t.Errorf("Message = %q, want %q", resp.Message, "backlog review started")
	}
}

func TestStartBacklogReview_HandlerError(t *testing.T) {
	p := &fakePlanningClientCmd{startBacklogReviewErr: errors.New("boom")}
	svc := newTestCommandService(p, &fakeCeremonyClientCmd{})

	_, err := svc.StartBacklogReview(ctxWithClientID("client-1"), &proxyv1.StartBacklogReviewRequest{
		RequestId:  "req-1",
		CeremonyId: "cer-1",
	})
	if err == nil {
		t.Fatal("expected error")
	}
}

func TestStartBacklogReview_ValidationError(t *testing.T) {
	svc := newTestCommandService(&fakePlanningClientCmd{}, &fakeCeremonyClientCmd{})
	// missing CeremonyId
	_, err := svc.StartBacklogReview(ctxWithClientID("client-1"), &proxyv1.StartBacklogReviewRequest{
		RequestId: "req-1",
	})
	if err == nil {
		t.Fatal("expected error for missing ceremony_id")
	}
}

// ---------------------------------------------------------------------------
// CreateBacklogReview
// ---------------------------------------------------------------------------

func TestCreateBacklogReview_Success(t *testing.T) {
	p := &fakePlanningClientCmd{
		createBacklogReviewResult: ports.BacklogReviewResult{
			CeremonyID: "cer-2",
			Status:     "created",
			StoryIDs:   []string{"s1", "s2"},
			CreatedBy:  "client-1",
			ReviewResults: []ports.StoryReviewResultItem{
				{
					StoryID:        "s1",
					ApprovalStatus: "pending",
					PlanPreliminary: ports.PlanPreliminaryResult{
						Title:               "Plan for s1",
						Description:         "desc",
						AcceptanceCriteria:  []string{"ac1"},
						TechnicalNotes:      "notes",
						Roles:               []string{"dev"},
						EstimatedComplexity: "medium",
						Dependencies:        []string{"dep-1"},
						TasksOutline:        []string{"task-1"},
					},
					ArchitectFeedback:  "looks good",
					QAFeedback:         "needs tests",
					DevopsFeedback:     "ok",
					Recommendations:    []string{"rec-1"},
					PONotes:            "approved",
					POConcerns:         "none",
					PriorityAdjustment: "high",
					POPriorityReason:   "critical path",
					PlanID:             "plan-1",
				},
			},
		},
	}
	svc := newTestCommandService(p, &fakeCeremonyClientCmd{})

	resp, err := svc.CreateBacklogReview(ctxWithClientID("client-1"), &proxyv1.CreateBacklogReviewRequest{
		RequestId: "req-1",
		StoryIds:  []string{"s1", "s2"},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !resp.Success {
		t.Error("Success should be true")
	}
	if resp.Message != "backlog review created" {
		t.Errorf("Message = %q, want %q", resp.Message, "backlog review created")
	}
	if resp.Ceremony == nil {
		t.Fatal("Ceremony should not be nil")
	}
	if resp.Ceremony.CeremonyId != "cer-2" {
		t.Errorf("Ceremony.CeremonyId = %q, want %q", resp.Ceremony.CeremonyId, "cer-2")
	}
	if len(resp.Ceremony.ReviewResults) != 1 {
		t.Fatalf("ReviewResults len = %d, want 1", len(resp.Ceremony.ReviewResults))
	}
	sr := resp.Ceremony.ReviewResults[0]
	if sr.StoryId != "s1" {
		t.Errorf("StoryId = %q, want %q", sr.StoryId, "s1")
	}
	if sr.ApprovalStatus != "pending" {
		t.Errorf("ApprovalStatus = %q, want %q", sr.ApprovalStatus, "pending")
	}
	if sr.PlanPreliminary == nil {
		t.Fatal("PlanPreliminary should not be nil")
	}
	if sr.PlanPreliminary.Title != "Plan for s1" {
		t.Errorf("PlanPreliminary.Title = %q, want %q", sr.PlanPreliminary.Title, "Plan for s1")
	}
	if sr.ArchitectFeedback != "looks good" {
		t.Errorf("ArchitectFeedback = %q, want %q", sr.ArchitectFeedback, "looks good")
	}
	if sr.QaFeedback != "needs tests" {
		t.Errorf("QaFeedback = %q, want %q", sr.QaFeedback, "needs tests")
	}
	if sr.DevopsFeedback != "ok" {
		t.Errorf("DevopsFeedback = %q, want %q", sr.DevopsFeedback, "ok")
	}
	if sr.PoNotes != "approved" {
		t.Errorf("PoNotes = %q, want %q", sr.PoNotes, "approved")
	}
	if sr.PoConcerns != "none" {
		t.Errorf("PoConcerns = %q, want %q", sr.PoConcerns, "none")
	}
	if sr.PriorityAdjustment != "high" {
		t.Errorf("PriorityAdjustment = %q, want %q", sr.PriorityAdjustment, "high")
	}
	if sr.PoPriorityReason != "critical path" {
		t.Errorf("PoPriorityReason = %q, want %q", sr.PoPriorityReason, "critical path")
	}
	if sr.PlanId != "plan-1" {
		t.Errorf("PlanId = %q, want %q", sr.PlanId, "plan-1")
	}
	if len(sr.Recommendations) != 1 || sr.Recommendations[0] != "rec-1" {
		t.Errorf("Recommendations = %v, want [rec-1]", sr.Recommendations)
	}
	pp := sr.PlanPreliminary
	if pp.Description != "desc" {
		t.Errorf("PlanPreliminary.Description = %q, want %q", pp.Description, "desc")
	}
	if pp.TechnicalNotes != "notes" {
		t.Errorf("PlanPreliminary.TechnicalNotes = %q, want %q", pp.TechnicalNotes, "notes")
	}
	if pp.EstimatedComplexity != "medium" {
		t.Errorf("PlanPreliminary.EstimatedComplexity = %q, want %q", pp.EstimatedComplexity, "medium")
	}
	if len(pp.AcceptanceCriteria) != 1 || pp.AcceptanceCriteria[0] != "ac1" {
		t.Errorf("PlanPreliminary.AcceptanceCriteria = %v, want [ac1]", pp.AcceptanceCriteria)
	}
	if len(pp.Roles) != 1 || pp.Roles[0] != "dev" {
		t.Errorf("PlanPreliminary.Roles = %v, want [dev]", pp.Roles)
	}
	if len(pp.Dependencies) != 1 || pp.Dependencies[0] != "dep-1" {
		t.Errorf("PlanPreliminary.Dependencies = %v, want [dep-1]", pp.Dependencies)
	}
	if len(pp.TasksOutline) != 1 || pp.TasksOutline[0] != "task-1" {
		t.Errorf("PlanPreliminary.TasksOutline = %v, want [task-1]", pp.TasksOutline)
	}
}

func TestCreateBacklogReview_HandlerError(t *testing.T) {
	p := &fakePlanningClientCmd{createBacklogReviewErr: errors.New("boom")}
	svc := newTestCommandService(p, &fakeCeremonyClientCmd{})

	_, err := svc.CreateBacklogReview(ctxWithClientID("client-1"), &proxyv1.CreateBacklogReviewRequest{
		RequestId: "req-1",
		StoryIds:  []string{"s1"},
	})
	if err == nil {
		t.Fatal("expected error")
	}
}

func TestCreateBacklogReview_ValidationError(t *testing.T) {
	svc := newTestCommandService(&fakePlanningClientCmd{}, &fakeCeremonyClientCmd{})
	// missing RequestId
	_, err := svc.CreateBacklogReview(ctxWithClientID("client-1"), &proxyv1.CreateBacklogReviewRequest{})
	if err == nil {
		t.Fatal("expected error for missing request_id")
	}
}

// ---------------------------------------------------------------------------
// ApproveReviewPlan
// ---------------------------------------------------------------------------

func TestApproveReviewPlan_Success(t *testing.T) {
	p := &fakePlanningClientCmd{
		approveReviewPlanResult: ports.BacklogReviewResult{
			CeremonyID: "cer-1",
			Status:     "in_progress",
		},
		approveReviewPlanID: "plan-42",
	}
	svc := newTestCommandService(p, &fakeCeremonyClientCmd{})

	resp, err := svc.ApproveReviewPlan(ctxWithClientID("client-1"), &proxyv1.ApproveReviewPlanRequest{
		RequestId:          "req-1",
		CeremonyId:         "cer-1",
		StoryId:            "story-1",
		PoNotes:            "lgtm",
		PoConcerns:         "none",
		PriorityAdjustment: "high",
		PoPriorityReason:   "critical",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !resp.Success {
		t.Error("Success should be true")
	}
	if resp.PlanId != "plan-42" {
		t.Errorf("PlanId = %q, want %q", resp.PlanId, "plan-42")
	}
	if resp.Message != "review plan approved" {
		t.Errorf("Message = %q, want %q", resp.Message, "review plan approved")
	}
	if resp.Ceremony == nil {
		t.Fatal("Ceremony should not be nil")
	}
	if resp.Ceremony.CeremonyId != "cer-1" {
		t.Errorf("Ceremony.CeremonyId = %q, want %q", resp.Ceremony.CeremonyId, "cer-1")
	}
}

func TestApproveReviewPlan_HandlerError(t *testing.T) {
	p := &fakePlanningClientCmd{approveReviewPlanErr: errors.New("boom")}
	svc := newTestCommandService(p, &fakeCeremonyClientCmd{})

	_, err := svc.ApproveReviewPlan(ctxWithClientID("client-1"), &proxyv1.ApproveReviewPlanRequest{
		RequestId:  "req-1",
		CeremonyId: "cer-1",
		StoryId:    "story-1",
		PoNotes:    "notes",
	})
	if err == nil {
		t.Fatal("expected error")
	}
}

func TestApproveReviewPlan_ValidationError(t *testing.T) {
	svc := newTestCommandService(&fakePlanningClientCmd{}, &fakeCeremonyClientCmd{})
	// missing PoNotes
	_, err := svc.ApproveReviewPlan(ctxWithClientID("client-1"), &proxyv1.ApproveReviewPlanRequest{
		RequestId:  "req-1",
		CeremonyId: "cer-1",
		StoryId:    "story-1",
	})
	if err == nil {
		t.Fatal("expected error for missing po_notes")
	}
}

// ---------------------------------------------------------------------------
// RejectReviewPlan
// ---------------------------------------------------------------------------

func TestRejectReviewPlan_Success(t *testing.T) {
	p := &fakePlanningClientCmd{
		rejectReviewPlanResult: ports.BacklogReviewResult{
			CeremonyID: "cer-1",
			Status:     "in_progress",
		},
	}
	svc := newTestCommandService(p, &fakeCeremonyClientCmd{})

	resp, err := svc.RejectReviewPlan(ctxWithClientID("client-1"), &proxyv1.RejectReviewPlanRequest{
		RequestId:  "req-1",
		CeremonyId: "cer-1",
		StoryId:    "story-1",
		Reason:     "not ready",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !resp.Success {
		t.Error("Success should be true")
	}
	if resp.Message != "review plan rejected" {
		t.Errorf("Message = %q, want %q", resp.Message, "review plan rejected")
	}
	if resp.Ceremony == nil {
		t.Fatal("Ceremony should not be nil")
	}
	if resp.Ceremony.CeremonyId != "cer-1" {
		t.Errorf("Ceremony.CeremonyId = %q, want %q", resp.Ceremony.CeremonyId, "cer-1")
	}
}

func TestRejectReviewPlan_HandlerError(t *testing.T) {
	p := &fakePlanningClientCmd{rejectReviewPlanErr: errors.New("boom")}
	svc := newTestCommandService(p, &fakeCeremonyClientCmd{})

	_, err := svc.RejectReviewPlan(ctxWithClientID("client-1"), &proxyv1.RejectReviewPlanRequest{
		RequestId:  "req-1",
		CeremonyId: "cer-1",
		StoryId:    "story-1",
		Reason:     "not ready",
	})
	if err == nil {
		t.Fatal("expected error")
	}
}

func TestRejectReviewPlan_ValidationError(t *testing.T) {
	svc := newTestCommandService(&fakePlanningClientCmd{}, &fakeCeremonyClientCmd{})
	// missing Reason
	_, err := svc.RejectReviewPlan(ctxWithClientID("client-1"), &proxyv1.RejectReviewPlanRequest{
		RequestId:  "req-1",
		CeremonyId: "cer-1",
		StoryId:    "story-1",
	})
	if err == nil {
		t.Fatal("expected error for missing reason")
	}
}

// ---------------------------------------------------------------------------
// CompleteBacklogReview
// ---------------------------------------------------------------------------

func TestCompleteBacklogReview_Success(t *testing.T) {
	p := &fakePlanningClientCmd{
		completeBacklogResult: ports.BacklogReviewResult{
			CeremonyID: "cer-1",
			Status:     "completed",
		},
	}
	svc := newTestCommandService(p, &fakeCeremonyClientCmd{})

	resp, err := svc.CompleteBacklogReview(ctxWithClientID("client-1"), &proxyv1.CompleteBacklogReviewRequest{
		RequestId:  "req-1",
		CeremonyId: "cer-1",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !resp.Success {
		t.Error("Success should be true")
	}
	if resp.Message != "backlog review completed" {
		t.Errorf("Message = %q, want %q", resp.Message, "backlog review completed")
	}
	if resp.Ceremony == nil {
		t.Fatal("Ceremony should not be nil")
	}
	if resp.Ceremony.Status != "completed" {
		t.Errorf("Ceremony.Status = %q, want %q", resp.Ceremony.Status, "completed")
	}
}

func TestCompleteBacklogReview_HandlerError(t *testing.T) {
	p := &fakePlanningClientCmd{completeBacklogErr: errors.New("boom")}
	svc := newTestCommandService(p, &fakeCeremonyClientCmd{})

	_, err := svc.CompleteBacklogReview(ctxWithClientID("client-1"), &proxyv1.CompleteBacklogReviewRequest{
		RequestId:  "req-1",
		CeremonyId: "cer-1",
	})
	if err == nil {
		t.Fatal("expected error")
	}
}

func TestCompleteBacklogReview_ValidationError(t *testing.T) {
	svc := newTestCommandService(&fakePlanningClientCmd{}, &fakeCeremonyClientCmd{})
	// missing CeremonyId
	_, err := svc.CompleteBacklogReview(ctxWithClientID("client-1"), &proxyv1.CompleteBacklogReviewRequest{
		RequestId: "req-1",
	})
	if err == nil {
		t.Fatal("expected error for missing ceremony_id")
	}
}

// ---------------------------------------------------------------------------
// CancelBacklogReview
// ---------------------------------------------------------------------------

func TestCancelBacklogReview_Success(t *testing.T) {
	p := &fakePlanningClientCmd{
		cancelBacklogResult: ports.BacklogReviewResult{
			CeremonyID: "cer-1",
			Status:     "cancelled",
		},
	}
	svc := newTestCommandService(p, &fakeCeremonyClientCmd{})

	resp, err := svc.CancelBacklogReview(ctxWithClientID("client-1"), &proxyv1.CancelBacklogReviewRequest{
		RequestId:  "req-1",
		CeremonyId: "cer-1",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !resp.Success {
		t.Error("Success should be true")
	}
	if resp.Message != "backlog review cancelled" {
		t.Errorf("Message = %q, want %q", resp.Message, "backlog review cancelled")
	}
	if resp.Ceremony == nil {
		t.Fatal("Ceremony should not be nil")
	}
	if resp.Ceremony.Status != "cancelled" {
		t.Errorf("Ceremony.Status = %q, want %q", resp.Ceremony.Status, "cancelled")
	}
}

func TestCancelBacklogReview_HandlerError(t *testing.T) {
	p := &fakePlanningClientCmd{cancelBacklogErr: errors.New("boom")}
	svc := newTestCommandService(p, &fakeCeremonyClientCmd{})

	_, err := svc.CancelBacklogReview(ctxWithClientID("client-1"), &proxyv1.CancelBacklogReviewRequest{
		RequestId:  "req-1",
		CeremonyId: "cer-1",
	})
	if err == nil {
		t.Fatal("expected error")
	}
}

func TestCancelBacklogReview_ValidationError(t *testing.T) {
	svc := newTestCommandService(&fakePlanningClientCmd{}, &fakeCeremonyClientCmd{})
	// missing CeremonyId
	_, err := svc.CancelBacklogReview(ctxWithClientID("client-1"), &proxyv1.CancelBacklogReviewRequest{
		RequestId: "req-1",
	})
	if err == nil {
		t.Fatal("expected error for missing ceremony_id")
	}
}

// ---------------------------------------------------------------------------
// ApproveDecision
// ---------------------------------------------------------------------------

func TestApproveDecision_Success(t *testing.T) {
	svc := newTestCommandService(&fakePlanningClientCmd{}, &fakeCeremonyClientCmd{})

	resp, err := svc.ApproveDecision(ctxWithClientID("client-1"), &proxyv1.ApproveDecisionRequest{
		StoryId:    "story-1",
		DecisionId: "dec-1",
		Comment:    "looks good",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !resp.Success {
		t.Error("Success should be true")
	}
	if resp.Message != "decision approved" {
		t.Errorf("Message = %q, want %q", resp.Message, "decision approved")
	}
}

func TestApproveDecision_HandlerError(t *testing.T) {
	p := &fakePlanningClientCmd{approveDecisionErr: errors.New("boom")}
	svc := newTestCommandService(p, &fakeCeremonyClientCmd{})

	_, err := svc.ApproveDecision(ctxWithClientID("client-1"), &proxyv1.ApproveDecisionRequest{
		StoryId:    "story-1",
		DecisionId: "dec-1",
		Comment:    "ok",
	})
	if err == nil {
		t.Fatal("expected error")
	}
}

func TestApproveDecision_ValidationError(t *testing.T) {
	svc := newTestCommandService(&fakePlanningClientCmd{}, &fakeCeremonyClientCmd{})
	// missing DecisionId
	_, err := svc.ApproveDecision(ctxWithClientID("client-1"), &proxyv1.ApproveDecisionRequest{
		StoryId: "story-1",
	})
	if err == nil {
		t.Fatal("expected error for missing decision_id")
	}
}

// ---------------------------------------------------------------------------
// RejectDecision
// ---------------------------------------------------------------------------

func TestRejectDecision_Success(t *testing.T) {
	svc := newTestCommandService(&fakePlanningClientCmd{}, &fakeCeremonyClientCmd{})

	resp, err := svc.RejectDecision(ctxWithClientID("client-1"), &proxyv1.RejectDecisionRequest{
		StoryId:    "story-1",
		DecisionId: "dec-1",
		Reason:     "not aligned",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !resp.Success {
		t.Error("Success should be true")
	}
	if resp.Message != "decision rejected" {
		t.Errorf("Message = %q, want %q", resp.Message, "decision rejected")
	}
}

func TestRejectDecision_HandlerError(t *testing.T) {
	p := &fakePlanningClientCmd{rejectDecisionErr: errors.New("boom")}
	svc := newTestCommandService(p, &fakeCeremonyClientCmd{})

	_, err := svc.RejectDecision(ctxWithClientID("client-1"), &proxyv1.RejectDecisionRequest{
		StoryId:    "story-1",
		DecisionId: "dec-1",
		Reason:     "nope",
	})
	if err == nil {
		t.Fatal("expected error")
	}
}

func TestRejectDecision_ValidationError(t *testing.T) {
	svc := newTestCommandService(&fakePlanningClientCmd{}, &fakeCeremonyClientCmd{})
	// missing Reason
	_, err := svc.RejectDecision(ctxWithClientID("client-1"), &proxyv1.RejectDecisionRequest{
		StoryId:    "story-1",
		DecisionId: "dec-1",
	})
	if err == nil {
		t.Fatal("expected error for missing reason")
	}
}

// ---------------------------------------------------------------------------
// backlogReviewResultToProto — verify full field mapping
// ---------------------------------------------------------------------------

func TestBacklogReviewResultToProto_EmptyReviewResults(t *testing.T) {
	result := ports.BacklogReviewResult{
		CeremonyID:  "cer-1",
		Status:      "created",
		CreatedBy:   "user-1",
		CreatedAt:   "2024-01-01T00:00:00Z",
		UpdatedAt:   "2024-01-02T00:00:00Z",
		StartedAt:   "2024-01-01T01:00:00Z",
		CompletedAt: "2024-01-01T02:00:00Z",
		StoryIDs:    []string{"s1"},
	}

	proto := backlogReviewResultToProto(result)

	if proto.CeremonyId != "cer-1" {
		t.Errorf("CeremonyId = %q, want %q", proto.CeremonyId, "cer-1")
	}
	if proto.Status != "created" {
		t.Errorf("Status = %q, want %q", proto.Status, "created")
	}
	if proto.CreatedBy != "user-1" {
		t.Errorf("CreatedBy = %q, want %q", proto.CreatedBy, "user-1")
	}
	if proto.CreatedAt != "2024-01-01T00:00:00Z" {
		t.Errorf("CreatedAt = %q, want %q", proto.CreatedAt, "2024-01-01T00:00:00Z")
	}
	if proto.UpdatedAt != "2024-01-02T00:00:00Z" {
		t.Errorf("UpdatedAt = %q, want %q", proto.UpdatedAt, "2024-01-02T00:00:00Z")
	}
	if proto.StartedAt != "2024-01-01T01:00:00Z" {
		t.Errorf("StartedAt = %q, want %q", proto.StartedAt, "2024-01-01T01:00:00Z")
	}
	if proto.CompletedAt != "2024-01-01T02:00:00Z" {
		t.Errorf("CompletedAt = %q, want %q", proto.CompletedAt, "2024-01-01T02:00:00Z")
	}
	if len(proto.StoryIds) != 1 || proto.StoryIds[0] != "s1" {
		t.Errorf("StoryIds = %v, want [s1]", proto.StoryIds)
	}
	if len(proto.ReviewResults) != 0 {
		t.Errorf("ReviewResults len = %d, want 0", len(proto.ReviewResults))
	}
}

func TestStoryReviewResultToProto_AllFields(t *testing.T) {
	sr := ports.StoryReviewResultItem{
		StoryID:            "s1",
		ArchitectFeedback:  "arch",
		QAFeedback:         "qa",
		DevopsFeedback:     "devops",
		ApprovalStatus:     "approved",
		ReviewedAt:         "2024-01-01T00:00:00Z",
		ApprovedBy:         "user-1",
		ApprovedAt:         "2024-01-01T01:00:00Z",
		RejectedBy:         "",
		RejectedAt:         "",
		RejectionReason:    "",
		PONotes:            "notes",
		POConcerns:         "concerns",
		PriorityAdjustment: "high",
		POPriorityReason:   "reason",
		PlanID:             "plan-1",
		Recommendations:    []string{"rec-a", "rec-b"},
		PlanPreliminary: ports.PlanPreliminaryResult{
			Title: "plan title",
		},
	}

	proto := storyReviewResultToProto(sr)

	if proto.StoryId != "s1" {
		t.Errorf("StoryId = %q, want %q", proto.StoryId, "s1")
	}
	if proto.ArchitectFeedback != "arch" {
		t.Errorf("ArchitectFeedback = %q, want %q", proto.ArchitectFeedback, "arch")
	}
	if proto.QaFeedback != "qa" {
		t.Errorf("QaFeedback = %q, want %q", proto.QaFeedback, "qa")
	}
	if proto.DevopsFeedback != "devops" {
		t.Errorf("DevopsFeedback = %q, want %q", proto.DevopsFeedback, "devops")
	}
	if proto.ApprovalStatus != "approved" {
		t.Errorf("ApprovalStatus = %q, want %q", proto.ApprovalStatus, "approved")
	}
	if proto.ReviewedAt != "2024-01-01T00:00:00Z" {
		t.Errorf("ReviewedAt = %q, want %q", proto.ReviewedAt, "2024-01-01T00:00:00Z")
	}
	if proto.ApprovedBy != "user-1" {
		t.Errorf("ApprovedBy = %q, want %q", proto.ApprovedBy, "user-1")
	}
	if proto.ApprovedAt != "2024-01-01T01:00:00Z" {
		t.Errorf("ApprovedAt = %q, want %q", proto.ApprovedAt, "2024-01-01T01:00:00Z")
	}
	if proto.PoNotes != "notes" {
		t.Errorf("PoNotes = %q, want %q", proto.PoNotes, "notes")
	}
	if proto.PoConcerns != "concerns" {
		t.Errorf("PoConcerns = %q, want %q", proto.PoConcerns, "concerns")
	}
	if proto.PriorityAdjustment != "high" {
		t.Errorf("PriorityAdjustment = %q, want %q", proto.PriorityAdjustment, "high")
	}
	if proto.PoPriorityReason != "reason" {
		t.Errorf("PoPriorityReason = %q, want %q", proto.PoPriorityReason, "reason")
	}
	if proto.PlanId != "plan-1" {
		t.Errorf("PlanId = %q, want %q", proto.PlanId, "plan-1")
	}
	if len(proto.Recommendations) != 2 {
		t.Fatalf("Recommendations len = %d, want 2", len(proto.Recommendations))
	}
	if proto.PlanPreliminary == nil || proto.PlanPreliminary.Title != "plan title" {
		t.Errorf("PlanPreliminary.Title = %q, want %q", proto.PlanPreliminary.GetTitle(), "plan title")
	}
}

func TestPlanPreliminaryToProto(t *testing.T) {
	p := ports.PlanPreliminaryResult{
		Title:               "title",
		Description:         "desc",
		AcceptanceCriteria:  []string{"ac-1", "ac-2"},
		TechnicalNotes:      "tech",
		Roles:               []string{"dev", "qa"},
		EstimatedComplexity: "high",
		Dependencies:        []string{"dep-1"},
		TasksOutline:        []string{"task-1", "task-2"},
	}

	proto := planPreliminaryToProto(p)

	if proto.Title != "title" {
		t.Errorf("Title = %q, want %q", proto.Title, "title")
	}
	if proto.Description != "desc" {
		t.Errorf("Description = %q, want %q", proto.Description, "desc")
	}
	if proto.TechnicalNotes != "tech" {
		t.Errorf("TechnicalNotes = %q, want %q", proto.TechnicalNotes, "tech")
	}
	if proto.EstimatedComplexity != "high" {
		t.Errorf("EstimatedComplexity = %q, want %q", proto.EstimatedComplexity, "high")
	}
	if len(proto.AcceptanceCriteria) != 2 {
		t.Errorf("AcceptanceCriteria len = %d, want 2", len(proto.AcceptanceCriteria))
	}
	if len(proto.Roles) != 2 {
		t.Errorf("Roles len = %d, want 2", len(proto.Roles))
	}
	if len(proto.Dependencies) != 1 {
		t.Errorf("Dependencies len = %d, want 1", len(proto.Dependencies))
	}
	if len(proto.TasksOutline) != 2 {
		t.Errorf("TasksOutline len = %d, want 2", len(proto.TasksOutline))
	}
}
