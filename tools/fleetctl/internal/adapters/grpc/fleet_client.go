package grpc

import (
	"context"
	"fmt"

	proxyv1 "github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/gen/proxyv1"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// FleetClient implements ports.FleetClient over gRPC using generated stubs.
type FleetClient struct {
	conn         *Connection
	cmdClient    proxyv1.FleetCommandServiceClient
	qryClient    proxyv1.FleetQueryServiceClient
	enrollClient proxyv1.EnrollmentServiceClient
}

// NewFleetClient creates a FleetClient bound to the given Connection.
func NewFleetClient(conn *Connection) *FleetClient {
	return &FleetClient{
		conn:         conn,
		cmdClient:    proxyv1.NewFleetCommandServiceClient(conn.Conn()),
		qryClient:    proxyv1.NewFleetQueryServiceClient(conn.Conn()),
		enrollClient: proxyv1.NewEnrollmentServiceClient(conn.Conn()),
	}
}

// Enroll registers this device with the control plane using an API key and a CSR.
func (c *FleetClient) Enroll(ctx context.Context, apiKey, deviceID string, csrPEM []byte) (certPEM, caPEM []byte, clientID, expiresAt string, err error) {
	resp, err := c.enrollClient.Enroll(ctx, &proxyv1.EnrollRequest{
		ApiKey:        apiKey,
		CsrPem:        csrPEM,
		DeviceId:      deviceID,
		ClientVersion: "dev",
	})
	if err != nil {
		return nil, nil, "", "", fmt.Errorf("enroll RPC: %w", err)
	}
	return resp.GetClientCertPem(), resp.GetCaChainPem(), resp.GetClientId(), resp.GetExpiresAt(), nil
}

// Renew requests a new certificate using the existing mTLS identity.
func (c *FleetClient) Renew(ctx context.Context, csrPEM []byte) (certPEM, caPEM []byte, expiresAt string, err error) {
	resp, err := c.enrollClient.Renew(ctx, &proxyv1.RenewRequest{CsrPem: csrPEM})
	if err != nil {
		return nil, nil, "", fmt.Errorf("renew RPC: %w", err)
	}
	return resp.GetClientCertPem(), resp.GetCaChainPem(), resp.GetExpiresAt(), nil
}

// CreateProject creates a new project in the control plane.
func (c *FleetClient) CreateProject(ctx context.Context, requestID, name, description string) (domain.ProjectSummary, error) {
	resp, err := c.cmdClient.CreateProject(ctx, &proxyv1.CreateProjectRequest{
		RequestId:   requestID,
		Name:        name,
		Description: description,
	})
	if err != nil {
		return domain.ProjectSummary{}, fmt.Errorf("create_project RPC: %w", err)
	}
	return domain.ProjectSummary{
		ID:          resp.GetProjectId(),
		Name:        name,
		Description: description,
	}, nil
}

// CreateEpic creates a new epic under the given project.
func (c *FleetClient) CreateEpic(ctx context.Context, requestID, projectID, title, description string) (domain.EpicSummary, error) {
	resp, err := c.cmdClient.CreateEpic(ctx, &proxyv1.CreateEpicRequest{
		RequestId:   requestID,
		ProjectId:   projectID,
		Title:       title,
		Description: description,
	})
	if err != nil {
		return domain.EpicSummary{}, fmt.Errorf("create_epic RPC: %w", err)
	}
	return domain.EpicSummary{
		ID:          resp.GetEpicId(),
		ProjectID:   projectID,
		Title:       title,
		Description: description,
	}, nil
}

// CreateStory creates a new story under the given epic.
func (c *FleetClient) CreateStory(ctx context.Context, requestID, epicID, title, brief string) (domain.StorySummary, error) {
	resp, err := c.cmdClient.CreateStory(ctx, &proxyv1.CreateStoryRequest{
		RequestId: requestID,
		EpicId:    epicID,
		Title:     title,
		Brief:     brief,
	})
	if err != nil {
		return domain.StorySummary{}, fmt.Errorf("create_story RPC: %w", err)
	}
	return domain.StorySummary{
		ID:    resp.GetStoryId(),
		EpicID: epicID,
		Title: title,
		Brief: brief,
	}, nil
}

// TransitionStory moves a story to the specified target state.
func (c *FleetClient) TransitionStory(ctx context.Context, storyID, targetState string) error {
	resp, err := c.cmdClient.TransitionStory(ctx, &proxyv1.TransitionStoryRequest{
		StoryId:     storyID,
		TargetState: targetState,
	})
	if err != nil {
		return fmt.Errorf("transition_story RPC: %w", err)
	}
	if !resp.GetSuccess() {
		return fmt.Errorf("transition failed: %s", resp.GetMessage())
	}
	return nil
}

// StartCeremony kicks off a ceremony instance for the given story.
func (c *FleetClient) StartCeremony(ctx context.Context, requestID, ceremonyID, definitionName, storyID string, stepIDs []string) (domain.CeremonyStatus, error) {
	resp, err := c.cmdClient.StartPlanningCeremony(ctx, &proxyv1.StartPlanningCeremonyRequest{
		RequestId:      requestID,
		CeremonyId:     ceremonyID,
		DefinitionName: definitionName,
		StoryId:        storyID,
		StepIds:        stepIDs,
	})
	if err != nil {
		return domain.CeremonyStatus{}, fmt.Errorf("start_ceremony RPC: %w", err)
	}
	if resp.GetStatus() == "FAILED" || resp.GetStatus() == "ERROR" {
		return domain.CeremonyStatus{}, fmt.Errorf("start ceremony failed: %s", resp.GetMessage())
	}
	return domain.CeremonyStatus{
		InstanceID: resp.GetInstanceId(),
		Status:     resp.GetStatus(),
	}, nil
}

// ListProjects returns projects visible to the authenticated identity.
func (c *FleetClient) ListProjects(ctx context.Context, statusFilter string, limit, offset int32) ([]domain.ProjectSummary, int32, error) {
	resp, err := c.qryClient.ListProjects(ctx, &proxyv1.ListProjectsRequest{
		StatusFilter: statusFilter, Limit: limit, Offset: offset,
	})
	if err != nil {
		return nil, 0, fmt.Errorf("list_projects RPC: %w", err)
	}
	projects := make([]domain.ProjectSummary, 0, len(resp.GetProjects()))
	for _, p := range resp.GetProjects() {
		projects = append(projects, domain.ProjectSummary{
			ID:          p.GetProjectId(),
			Name:        p.GetName(),
			Description: p.GetDescription(),
			Status:      p.GetStatus(),
			Owner:       p.GetOwner(),
			CreatedAt:   p.GetCreatedAt(),
			UpdatedAt:   p.GetUpdatedAt(),
		})
	}
	return projects, resp.GetTotalCount(), nil
}

// ListEpics returns epics belonging to a project with optional status filter and pagination.
func (c *FleetClient) ListEpics(ctx context.Context, projectID, statusFilter string, limit, offset int32) ([]domain.EpicSummary, int32, error) {
	resp, err := c.qryClient.ListEpics(ctx, &proxyv1.ListEpicsRequest{
		ProjectId: projectID, StatusFilter: statusFilter, Limit: limit, Offset: offset,
	})
	if err != nil {
		return nil, 0, fmt.Errorf("list_epics RPC: %w", err)
	}
	epics := make([]domain.EpicSummary, 0, len(resp.GetEpics()))
	for _, e := range resp.GetEpics() {
		epics = append(epics, domain.EpicSummary{
			ID:          e.GetEpicId(),
			ProjectID:   e.GetProjectId(),
			Title:       e.GetTitle(),
			Description: e.GetDescription(),
			Status:      e.GetStatus(),
			CreatedAt:   e.GetCreatedAt(),
			UpdatedAt:   e.GetUpdatedAt(),
		})
	}
	return epics, resp.GetTotalCount(), nil
}

// ListStories returns stories with optional filtering and pagination.
func (c *FleetClient) ListStories(ctx context.Context, epicID, stateFilter string, limit, offset int32) ([]domain.StorySummary, int32, error) {
	resp, err := c.qryClient.ListStories(ctx, &proxyv1.ListStoriesRequest{
		EpicId: epicID, StateFilter: stateFilter, Limit: limit, Offset: offset,
	})
	if err != nil {
		return nil, 0, fmt.Errorf("list_stories RPC: %w", err)
	}
	stories := make([]domain.StorySummary, 0, len(resp.GetStories()))
	for _, s := range resp.GetStories() {
		stories = append(stories, domain.StorySummary{
			ID:        s.GetStoryId(),
			EpicID:    s.GetEpicId(),
			Title:     s.GetTitle(),
			Brief:     s.GetBrief(),
			State:     s.GetState(),
			DorScore:  s.GetDorScore(),
			CreatedBy: s.GetCreatedBy(),
			CreatedAt: s.GetCreatedAt(),
			UpdatedAt: s.GetUpdatedAt(),
		})
	}
	return stories, resp.GetTotalCount(), nil
}

// CreateTask creates a new task under the given story.
func (c *FleetClient) CreateTask(ctx context.Context, requestID, storyID, title, description, taskType, assignedTo string, estimatedHours, priority int32) (domain.TaskSummary, error) {
	resp, err := c.cmdClient.CreateTask(ctx, &proxyv1.CreateTaskRequest{
		RequestId:      requestID,
		StoryId:        storyID,
		Title:          title,
		Description:    description,
		Type:           taskType,
		AssignedTo:     assignedTo,
		EstimatedHours: estimatedHours,
		Priority:       priority,
	})
	if err != nil {
		return domain.TaskSummary{}, fmt.Errorf("create_task RPC: %w", err)
	}
	return domain.TaskSummary{
		ID:             resp.GetTaskId(),
		StoryID:        storyID,
		Title:          title,
		Description:    description,
		Type:           taskType,
		AssignedTo:     assignedTo,
		EstimatedHours: estimatedHours,
		Priority:       priority,
	}, nil
}

// ListTasks returns tasks with optional filtering and pagination.
func (c *FleetClient) ListTasks(ctx context.Context, storyID, statusFilter string, limit, offset int32) ([]domain.TaskSummary, int32, error) {
	resp, err := c.qryClient.ListTasks(ctx, &proxyv1.ListTasksRequest{
		StoryId: storyID, StatusFilter: statusFilter, Limit: limit, Offset: offset,
	})
	if err != nil {
		return nil, 0, fmt.Errorf("list_tasks RPC: %w", err)
	}
	tasks := make([]domain.TaskSummary, 0, len(resp.GetTasks()))
	for _, t := range resp.GetTasks() {
		tasks = append(tasks, domain.TaskSummary{
			ID:             t.GetTaskId(),
			StoryID:        t.GetStoryId(),
			Title:          t.GetTitle(),
			Description:    t.GetDescription(),
			Type:           t.GetType(),
			Status:         t.GetStatus(),
			AssignedTo:     t.GetAssignedTo(),
			EstimatedHours: t.GetEstimatedHours(),
			Priority:       t.GetPriority(),
			CreatedAt:      t.GetCreatedAt(),
			UpdatedAt:      t.GetUpdatedAt(),
		})
	}
	return tasks, resp.GetTotalCount(), nil
}

// ListCeremonies returns ceremony instances with optional filtering and pagination.
func (c *FleetClient) ListCeremonies(ctx context.Context, storyID, statusFilter string, limit, offset int32) ([]domain.CeremonyStatus, int32, error) {
	resp, err := c.qryClient.ListCeremonyInstances(ctx, &proxyv1.ListCeremonyInstancesRequest{
		StateFilter: statusFilter,
		StoryId:     storyID,
		Limit:       limit,
		Offset:      offset,
	})
	if err != nil {
		return nil, 0, fmt.Errorf("list_ceremony_instances RPC: %w", err)
	}
	ceremonies := make([]domain.CeremonyStatus, 0, len(resp.GetCeremonies()))
	for _, cm := range resp.GetCeremonies() {
		ceremonies = append(ceremonies, ceremonyProtoToDomain(cm))
	}
	return ceremonies, resp.GetTotalCount(), nil
}

// GetCeremony returns the current status of a ceremony instance.
func (c *FleetClient) GetCeremony(ctx context.Context, instanceID string) (domain.CeremonyStatus, error) {
	resp, err := c.qryClient.GetCeremonyInstance(ctx, &proxyv1.GetCeremonyInstanceRequest{
		InstanceId: instanceID,
	})
	if err != nil {
		return domain.CeremonyStatus{}, fmt.Errorf("get_ceremony_instance RPC: %w", err)
	}
	return ceremonyProtoToDomain(resp.GetCeremony()), nil
}

func ceremonyProtoToDomain(m *proxyv1.CeremonyInstance) domain.CeremonyStatus {
	if m == nil {
		return domain.CeremonyStatus{}
	}
	return domain.CeremonyStatus{
		InstanceID:     m.GetInstanceId(),
		CeremonyID:     m.GetCeremonyId(),
		StoryID:        m.GetStoryId(),
		DefinitionName: m.GetDefinitionName(),
		CurrentState:   m.GetCurrentState(),
		Status:         m.GetStatus(),
		CorrelationID:  m.GetCorrelationId(),
		StepStatuses:   m.GetStepStatus(),
		StepOutputs:    m.GetStepOutputs(),
		CreatedAt:      m.GetCreatedAt(),
		UpdatedAt:      m.GetUpdatedAt(),
	}
}

// ApproveDecision approves a pending decision for the given story.
func (c *FleetClient) ApproveDecision(ctx context.Context, storyID, decisionID, comment string) error {
	resp, err := c.cmdClient.ApproveDecision(ctx, &proxyv1.ApproveDecisionRequest{
		StoryId: storyID, DecisionId: decisionID, Comment: comment,
	})
	if err != nil {
		return fmt.Errorf("approve_decision RPC: %w", err)
	}
	if !resp.GetSuccess() {
		return fmt.Errorf("approve decision failed: %s", resp.GetMessage())
	}
	return nil
}

// RejectDecision rejects a pending decision for the given story.
func (c *FleetClient) RejectDecision(ctx context.Context, storyID, decisionID, reason string) error {
	resp, err := c.cmdClient.RejectDecision(ctx, &proxyv1.RejectDecisionRequest{
		StoryId: storyID, DecisionId: decisionID, Reason: reason,
	})
	if err != nil {
		return fmt.Errorf("reject_decision RPC: %w", err)
	}
	if !resp.GetSuccess() {
		return fmt.Errorf("reject decision failed: %s", resp.GetMessage())
	}
	return nil
}

// CreateBacklogReview creates a new backlog review ceremony.
func (c *FleetClient) CreateBacklogReview(ctx context.Context, requestID string, storyIDs []string) (domain.BacklogReview, error) {
	resp, err := c.cmdClient.CreateBacklogReview(ctx, &proxyv1.CreateBacklogReviewRequest{
		RequestId: requestID, StoryIds: storyIDs,
	})
	if err != nil {
		return domain.BacklogReview{}, fmt.Errorf("create_backlog_review RPC: %w", err)
	}
	return backlogReviewProtoToDomain(resp.GetCeremony()), nil
}

// StartBacklogReview starts a backlog review ceremony.
func (c *FleetClient) StartBacklogReview(ctx context.Context, requestID, ceremonyID string) (domain.BacklogReview, int32, error) {
	resp, err := c.cmdClient.StartBacklogReview(ctx, &proxyv1.StartBacklogReviewRequest{
		RequestId: requestID, CeremonyId: ceremonyID,
	})
	if err != nil {
		return domain.BacklogReview{}, 0, fmt.Errorf("start_backlog_review RPC: %w", err)
	}
	return backlogReviewProtoToDomain(resp.GetCeremony()), resp.GetTotalDeliberationsSubmitted(), nil
}

// GetBacklogReview fetches a single backlog review ceremony.
func (c *FleetClient) GetBacklogReview(ctx context.Context, ceremonyID string) (domain.BacklogReview, error) {
	resp, err := c.qryClient.GetBacklogReview(ctx, &proxyv1.GetBacklogReviewRequest{
		CeremonyId: ceremonyID,
	})
	if err != nil {
		return domain.BacklogReview{}, fmt.Errorf("get_backlog_review RPC: %w", err)
	}
	return backlogReviewProtoToDomain(resp.GetCeremony()), nil
}

// ListBacklogReviews returns backlog review ceremonies with filtering.
func (c *FleetClient) ListBacklogReviews(ctx context.Context, statusFilter string, limit, offset int32) ([]domain.BacklogReview, int32, error) {
	resp, err := c.qryClient.ListBacklogReviews(ctx, &proxyv1.ListBacklogReviewsRequest{
		StatusFilter: statusFilter, Limit: limit, Offset: offset,
	})
	if err != nil {
		return nil, 0, fmt.Errorf("list_backlog_reviews RPC: %w", err)
	}
	reviews := make([]domain.BacklogReview, 0, len(resp.GetCeremonies()))
	for _, cer := range resp.GetCeremonies() {
		reviews = append(reviews, backlogReviewProtoToDomain(cer))
	}
	return reviews, resp.GetTotalCount(), nil
}

// ApproveReviewPlan approves a story's review plan.
func (c *FleetClient) ApproveReviewPlan(ctx context.Context, requestID, ceremonyID, storyID, poNotes, poConcerns, priorityAdj, prioReason string) (domain.BacklogReview, string, error) {
	resp, err := c.cmdClient.ApproveReviewPlan(ctx, &proxyv1.ApproveReviewPlanRequest{
		RequestId:          requestID,
		CeremonyId:         ceremonyID,
		StoryId:            storyID,
		PoNotes:            poNotes,
		PoConcerns:         poConcerns,
		PriorityAdjustment: priorityAdj,
		PoPriorityReason:   prioReason,
	})
	if err != nil {
		return domain.BacklogReview{}, "", fmt.Errorf("approve_review_plan RPC: %w", err)
	}
	return backlogReviewProtoToDomain(resp.GetCeremony()), resp.GetPlanId(), nil
}

// RejectReviewPlan rejects a story's review plan.
func (c *FleetClient) RejectReviewPlan(ctx context.Context, requestID, ceremonyID, storyID, reason string) (domain.BacklogReview, error) {
	resp, err := c.cmdClient.RejectReviewPlan(ctx, &proxyv1.RejectReviewPlanRequest{
		RequestId: requestID, CeremonyId: ceremonyID, StoryId: storyID, Reason: reason,
	})
	if err != nil {
		return domain.BacklogReview{}, fmt.Errorf("reject_review_plan RPC: %w", err)
	}
	return backlogReviewProtoToDomain(resp.GetCeremony()), nil
}

// CompleteBacklogReview marks a backlog review ceremony as completed.
func (c *FleetClient) CompleteBacklogReview(ctx context.Context, requestID, ceremonyID string) (domain.BacklogReview, error) {
	resp, err := c.cmdClient.CompleteBacklogReview(ctx, &proxyv1.CompleteBacklogReviewRequest{
		RequestId: requestID, CeremonyId: ceremonyID,
	})
	if err != nil {
		return domain.BacklogReview{}, fmt.Errorf("complete_backlog_review RPC: %w", err)
	}
	return backlogReviewProtoToDomain(resp.GetCeremony()), nil
}

// CancelBacklogReview cancels a backlog review ceremony.
func (c *FleetClient) CancelBacklogReview(ctx context.Context, requestID, ceremonyID string) (domain.BacklogReview, error) {
	resp, err := c.cmdClient.CancelBacklogReview(ctx, &proxyv1.CancelBacklogReviewRequest{
		RequestId: requestID, CeremonyId: ceremonyID,
	})
	if err != nil {
		return domain.BacklogReview{}, fmt.Errorf("cancel_backlog_review RPC: %w", err)
	}
	return backlogReviewProtoToDomain(resp.GetCeremony()), nil
}

func backlogReviewProtoToDomain(m *proxyv1.BacklogReview) domain.BacklogReview {
	if m == nil {
		return domain.BacklogReview{}
	}
	results := make([]domain.StoryReviewResult, 0, len(m.GetReviewResults()))
	for _, r := range m.GetReviewResults() {
		var pp domain.PlanPreliminary
		if r.GetPlanPreliminary() != nil {
			p := r.GetPlanPreliminary()
			pp = domain.PlanPreliminary{
				Title:               p.GetTitle(),
				Description:         p.GetDescription(),
				TechnicalNotes:      p.GetTechnicalNotes(),
				EstimatedComplexity: p.GetEstimatedComplexity(),
				AcceptanceCriteria:  p.GetAcceptanceCriteria(),
				Roles:               p.GetRoles(),
				Dependencies:        p.GetDependencies(),
				TasksOutline:        p.GetTasksOutline(),
			}
		}
		results = append(results, domain.StoryReviewResult{
			StoryID:            r.GetStoryId(),
			ArchitectFeedback:  r.GetArchitectFeedback(),
			QAFeedback:         r.GetQaFeedback(),
			DevopsFeedback:     r.GetDevopsFeedback(),
			ApprovalStatus:     r.GetApprovalStatus(),
			ReviewedAt:         r.GetReviewedAt(),
			ApprovedBy:         r.GetApprovedBy(),
			ApprovedAt:         r.GetApprovedAt(),
			RejectedBy:         r.GetRejectedBy(),
			RejectedAt:         r.GetRejectedAt(),
			RejectionReason:    r.GetRejectionReason(),
			PONotes:            r.GetPoNotes(),
			POConcerns:         r.GetPoConcerns(),
			PriorityAdjustment: r.GetPriorityAdjustment(),
			POPriorityReason:   r.GetPoPriorityReason(),
			PlanID:             r.GetPlanId(),
			Recommendations:    r.GetRecommendations(),
			PlanPreliminary:    pp,
		})
	}
	return domain.BacklogReview{
		CeremonyID:    m.GetCeremonyId(),
		Status:        m.GetStatus(),
		CreatedBy:     m.GetCreatedBy(),
		CreatedAt:     m.GetCreatedAt(),
		UpdatedAt:     m.GetUpdatedAt(),
		StartedAt:     m.GetStartedAt(),
		CompletedAt:   m.GetCompletedAt(),
		StoryIDs:      m.GetStoryIds(),
		ReviewResults: results,
	}
}

// Close releases the underlying gRPC connection.
func (c *FleetClient) Close() error {
	return c.conn.Close()
}
