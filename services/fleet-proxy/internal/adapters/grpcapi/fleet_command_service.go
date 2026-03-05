package grpcapi

import (
	"context"

	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	proxyv1 "github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/gen/proxyv1"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/adapters/grpcapi/interceptors"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/command"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

// FleetCommandService handles write-side gRPC RPCs.
type FleetCommandService struct {
	proxyv1.UnimplementedFleetCommandServiceServer

	createProject         *command.CreateProjectHandler
	createEpic            *command.CreateEpicHandler
	createStory           *command.CreateStoryHandler
	transitionStory       *command.TransitionStoryHandler
	createTask            *command.CreateTaskHandler
	startCeremony         *command.StartCeremonyHandler
	startBacklogReview    *command.StartBacklogReviewHandler
	approveDecision       *command.ApproveDecisionHandler
	rejectDecision        *command.RejectDecisionHandler
	createBacklogReview   *command.CreateBacklogReviewHandler
	approveReviewPlan     *command.ApproveReviewPlanHandler
	rejectReviewPlan      *command.RejectReviewPlanHandler
	completeBacklogReview *command.CompleteBacklogReviewHandler
	cancelBacklogReview   *command.CancelBacklogReviewHandler
}

// NewFleetCommandService creates a FleetCommandService wired to all command handlers.
func NewFleetCommandService(
	createProject *command.CreateProjectHandler,
	createEpic *command.CreateEpicHandler,
	createStory *command.CreateStoryHandler,
	transitionStory *command.TransitionStoryHandler,
	createTask *command.CreateTaskHandler,
	startCeremony *command.StartCeremonyHandler,
	startBacklogReview *command.StartBacklogReviewHandler,
	approveDecision *command.ApproveDecisionHandler,
	rejectDecision *command.RejectDecisionHandler,
	createBacklogReview *command.CreateBacklogReviewHandler,
	approveReviewPlan *command.ApproveReviewPlanHandler,
	rejectReviewPlan *command.RejectReviewPlanHandler,
	completeBacklogReview *command.CompleteBacklogReviewHandler,
	cancelBacklogReview *command.CancelBacklogReviewHandler,
) *FleetCommandService {
	return &FleetCommandService{
		createProject:         createProject,
		createEpic:            createEpic,
		createStory:           createStory,
		transitionStory:       transitionStory,
		createTask:            createTask,
		startCeremony:         startCeremony,
		startBacklogReview:    startBacklogReview,
		approveDecision:       approveDecision,
		rejectDecision:        rejectDecision,
		createBacklogReview:   createBacklogReview,
		approveReviewPlan:     approveReviewPlan,
		rejectReviewPlan:      rejectReviewPlan,
		completeBacklogReview: completeBacklogReview,
		cancelBacklogReview:   cancelBacklogReview,
	}
}

func (s *FleetCommandService) CreateProject(ctx context.Context, req *proxyv1.CreateProjectRequest) (*proxyv1.CreateProjectResponse, error) {
	clientID := interceptors.ClientIDFromContext(ctx)
	projectID, err := s.createProject.Handle(ctx, command.CreateProjectCmd{
		RequestID:   req.GetRequestId(),
		Name:        req.GetName(),
		Description: req.GetDescription(),
		RequestedBy: clientID,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "create project: %v", err)
	}
	return &proxyv1.CreateProjectResponse{ProjectId: projectID, Success: true, Message: "project created"}, nil
}

func (s *FleetCommandService) CreateEpic(ctx context.Context, req *proxyv1.CreateEpicRequest) (*proxyv1.CreateEpicResponse, error) {
	clientID := interceptors.ClientIDFromContext(ctx)
	epicID, err := s.createEpic.Handle(ctx, command.CreateEpicCmd{
		RequestID:   req.GetRequestId(),
		ProjectID:   req.GetProjectId(),
		Title:       req.GetTitle(),
		Description: req.GetDescription(),
		RequestedBy: clientID,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "create epic: %v", err)
	}
	return &proxyv1.CreateEpicResponse{EpicId: epicID, Success: true, Message: "epic created"}, nil
}

func (s *FleetCommandService) CreateStory(ctx context.Context, req *proxyv1.CreateStoryRequest) (*proxyv1.CreateStoryResponse, error) {
	clientID := interceptors.ClientIDFromContext(ctx)
	storyID, err := s.createStory.Handle(ctx, command.CreateStoryCmd{
		RequestID:   req.GetRequestId(),
		EpicID:      req.GetEpicId(),
		Title:       req.GetTitle(),
		Brief:       req.GetBrief(),
		RequestedBy: clientID,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "create story: %v", err)
	}
	return &proxyv1.CreateStoryResponse{StoryId: storyID, Success: true, Message: "story created"}, nil
}

func (s *FleetCommandService) TransitionStory(ctx context.Context, req *proxyv1.TransitionStoryRequest) (*proxyv1.TransitionStoryResponse, error) {
	clientID := interceptors.ClientIDFromContext(ctx)
	err := s.transitionStory.Handle(ctx, command.TransitionStoryCmd{
		StoryID:     req.GetStoryId(),
		TargetState: req.GetTargetState(),
		RequestedBy: clientID,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "transition story: %v", err)
	}
	return &proxyv1.TransitionStoryResponse{Success: true, Message: "story transitioned"}, nil
}

func (s *FleetCommandService) CreateTask(ctx context.Context, req *proxyv1.CreateTaskRequest) (*proxyv1.CreateTaskResponse, error) {
	clientID := interceptors.ClientIDFromContext(ctx)
	taskID, err := s.createTask.Handle(ctx, command.CreateTaskCmd{
		RequestID:      req.GetRequestId(),
		StoryID:        req.GetStoryId(),
		Title:          req.GetTitle(),
		Description:    req.GetDescription(),
		Type:           req.GetType(),
		AssignedTo:     req.GetAssignedTo(),
		EstimatedHours: req.GetEstimatedHours(),
		Priority:       req.GetPriority(),
		RequestedBy:    clientID,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "create task: %v", err)
	}
	return &proxyv1.CreateTaskResponse{TaskId: taskID, Success: true, Message: "task created"}, nil
}

func (s *FleetCommandService) StartPlanningCeremony(ctx context.Context, req *proxyv1.StartPlanningCeremonyRequest) (*proxyv1.StartPlanningCeremonyResponse, error) {
	clientID := interceptors.ClientIDFromContext(ctx)
	instanceID, err := s.startCeremony.Handle(ctx, command.StartCeremonyCmd{
		RequestID:      req.GetRequestId(),
		CeremonyID:     req.GetCeremonyId(),
		DefinitionName: req.GetDefinitionName(),
		StoryID:        req.GetStoryId(),
		StepIDs:        req.GetStepIds(),
		RequestedBy:    clientID,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "start planning ceremony: %v", err)
	}
	return &proxyv1.StartPlanningCeremonyResponse{InstanceId: instanceID, Status: "started", Message: "ceremony started"}, nil
}

func (s *FleetCommandService) StartBacklogReview(ctx context.Context, req *proxyv1.StartBacklogReviewRequest) (*proxyv1.StartBacklogReviewResponse, error) {
	clientID := interceptors.ClientIDFromContext(ctx)
	result, reviewCount, err := s.startBacklogReview.Handle(ctx, command.StartBacklogReviewCmd{
		RequestID:   req.GetRequestId(),
		CeremonyID:  req.GetCeremonyId(),
		RequestedBy: clientID,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "start backlog review: %v", err)
	}
	return &proxyv1.StartBacklogReviewResponse{
		Ceremony:                    backlogReviewResultToProto(result),
		Success:                     true,
		Message:                     "backlog review started",
		TotalDeliberationsSubmitted: reviewCount,
	}, nil
}

func (s *FleetCommandService) CreateBacklogReview(ctx context.Context, req *proxyv1.CreateBacklogReviewRequest) (*proxyv1.CreateBacklogReviewResponse, error) {
	clientID := interceptors.ClientIDFromContext(ctx)
	result, err := s.createBacklogReview.Handle(ctx, command.CreateBacklogReviewCmd{
		RequestID:   req.GetRequestId(),
		RequestedBy: clientID,
		StoryIDs:    req.GetStoryIds(),
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "create backlog review: %v", err)
	}
	return &proxyv1.CreateBacklogReviewResponse{
		Ceremony: backlogReviewResultToProto(result),
		Success:  true,
		Message:  "backlog review created",
	}, nil
}

func (s *FleetCommandService) ApproveReviewPlan(ctx context.Context, req *proxyv1.ApproveReviewPlanRequest) (*proxyv1.ApproveReviewPlanResponse, error) {
	clientID := interceptors.ClientIDFromContext(ctx)
	result, planID, err := s.approveReviewPlan.Handle(ctx, command.ApproveReviewPlanCmd{
		RequestID:          req.GetRequestId(),
		CeremonyID:         req.GetCeremonyId(),
		StoryID:            req.GetStoryId(),
		PONotes:            req.GetPoNotes(),
		POConcerns:         req.GetPoConcerns(),
		PriorityAdjustment: req.GetPriorityAdjustment(),
		POPriorityReason:   req.GetPoPriorityReason(),
		RequestedBy:        clientID,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "approve review plan: %v", err)
	}
	return &proxyv1.ApproveReviewPlanResponse{
		Ceremony: backlogReviewResultToProto(result),
		PlanId:   planID,
		Success:  true,
		Message:  "review plan approved",
	}, nil
}

func (s *FleetCommandService) RejectReviewPlan(ctx context.Context, req *proxyv1.RejectReviewPlanRequest) (*proxyv1.RejectReviewPlanResponse, error) {
	clientID := interceptors.ClientIDFromContext(ctx)
	result, err := s.rejectReviewPlan.Handle(ctx, command.RejectReviewPlanCmd{
		RequestID:   req.GetRequestId(),
		CeremonyID:  req.GetCeremonyId(),
		StoryID:     req.GetStoryId(),
		Reason:      req.GetReason(),
		RequestedBy: clientID,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "reject review plan: %v", err)
	}
	return &proxyv1.RejectReviewPlanResponse{
		Ceremony: backlogReviewResultToProto(result),
		Success:  true,
		Message:  "review plan rejected",
	}, nil
}

func (s *FleetCommandService) CompleteBacklogReview(ctx context.Context, req *proxyv1.CompleteBacklogReviewRequest) (*proxyv1.CompleteBacklogReviewResponse, error) {
	clientID := interceptors.ClientIDFromContext(ctx)
	result, err := s.completeBacklogReview.Handle(ctx, command.CompleteBacklogReviewCmd{
		RequestID:   req.GetRequestId(),
		CeremonyID:  req.GetCeremonyId(),
		RequestedBy: clientID,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "complete backlog review: %v", err)
	}
	return &proxyv1.CompleteBacklogReviewResponse{
		Ceremony: backlogReviewResultToProto(result),
		Success:  true,
		Message:  "backlog review completed",
	}, nil
}

func (s *FleetCommandService) CancelBacklogReview(ctx context.Context, req *proxyv1.CancelBacklogReviewRequest) (*proxyv1.CancelBacklogReviewResponse, error) {
	clientID := interceptors.ClientIDFromContext(ctx)
	result, err := s.cancelBacklogReview.Handle(ctx, command.CancelBacklogReviewCmd{
		RequestID:   req.GetRequestId(),
		CeremonyID:  req.GetCeremonyId(),
		RequestedBy: clientID,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "cancel backlog review: %v", err)
	}
	return &proxyv1.CancelBacklogReviewResponse{
		Ceremony: backlogReviewResultToProto(result),
		Success:  true,
		Message:  "backlog review cancelled",
	}, nil
}

func (s *FleetCommandService) ApproveDecision(ctx context.Context, req *proxyv1.ApproveDecisionRequest) (*proxyv1.ApproveDecisionResponse, error) {
	clientID := interceptors.ClientIDFromContext(ctx)
	err := s.approveDecision.Handle(ctx, command.ApproveDecisionCmd{
		StoryID:     req.GetStoryId(),
		DecisionID:  req.GetDecisionId(),
		Comment:     req.GetComment(),
		RequestedBy: clientID,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "approve decision: %v", err)
	}
	return &proxyv1.ApproveDecisionResponse{Success: true, Message: "decision approved"}, nil
}

func (s *FleetCommandService) RejectDecision(ctx context.Context, req *proxyv1.RejectDecisionRequest) (*proxyv1.RejectDecisionResponse, error) {
	clientID := interceptors.ClientIDFromContext(ctx)
	err := s.rejectDecision.Handle(ctx, command.RejectDecisionCmd{
		StoryID:     req.GetStoryId(),
		DecisionID:  req.GetDecisionId(),
		Reason:      req.GetReason(),
		RequestedBy: clientID,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "reject decision: %v", err)
	}
	return &proxyv1.RejectDecisionResponse{Success: true, Message: "decision rejected"}, nil
}

// ---------------------------------------------------------------------------
// Backlog review conversion helpers
// ---------------------------------------------------------------------------

func backlogReviewResultToProto(r ports.BacklogReviewResult) *proxyv1.BacklogReview {
	results := make([]*proxyv1.StoryReviewResult, len(r.ReviewResults))
	for i, sr := range r.ReviewResults {
		results[i] = storyReviewResultToProto(sr)
	}
	return &proxyv1.BacklogReview{
		CeremonyId:    r.CeremonyID,
		StoryIds:      r.StoryIDs,
		Status:        r.Status,
		ReviewResults: results,
		CreatedBy:     r.CreatedBy,
		CreatedAt:     r.CreatedAt,
		UpdatedAt:     r.UpdatedAt,
		StartedAt:     r.StartedAt,
		CompletedAt:   r.CompletedAt,
	}
}

func storyReviewResultToProto(sr ports.StoryReviewResultItem) *proxyv1.StoryReviewResult {
	return &proxyv1.StoryReviewResult{
		StoryId:            sr.StoryID,
		PlanPreliminary:    planPreliminaryToProto(sr.PlanPreliminary),
		ArchitectFeedback:  sr.ArchitectFeedback,
		QaFeedback:         sr.QAFeedback,
		DevopsFeedback:     sr.DevopsFeedback,
		Recommendations:    sr.Recommendations,
		ApprovalStatus:     sr.ApprovalStatus,
		ReviewedAt:         sr.ReviewedAt,
		ApprovedBy:         sr.ApprovedBy,
		ApprovedAt:         sr.ApprovedAt,
		RejectedBy:         sr.RejectedBy,
		RejectedAt:         sr.RejectedAt,
		RejectionReason:    sr.RejectionReason,
		PoNotes:            sr.PONotes,
		PoConcerns:         sr.POConcerns,
		PriorityAdjustment: sr.PriorityAdjustment,
		PoPriorityReason:   sr.POPriorityReason,
		PlanId:             sr.PlanID,
	}
}

func planPreliminaryToProto(p ports.PlanPreliminaryResult) *proxyv1.PlanPreliminary {
	return &proxyv1.PlanPreliminary{
		Title:               p.Title,
		Description:         p.Description,
		AcceptanceCriteria:  p.AcceptanceCriteria,
		TechnicalNotes:      p.TechnicalNotes,
		Roles:               p.Roles,
		EstimatedComplexity: p.EstimatedComplexity,
		Dependencies:        p.Dependencies,
		TasksOutline:        p.TasksOutline,
	}
}
