package grpc

import (
	"context"
	"fmt"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// FleetClient implements ports.FleetClient over gRPC. Method bodies are
// stubs until the proto-generated client stubs are available.
type FleetClient struct {
	conn *Connection
}

// NewFleetClient creates a FleetClient bound to the given Connection.
func NewFleetClient(conn *Connection) *FleetClient {
	return &FleetClient{conn: conn}
}

// Enroll registers this device with the control plane using an API key
// and a CSR. Uses a hand-crafted gRPC call matching the proto wire format.
func (c *FleetClient) Enroll(ctx context.Context, apiKey, deviceID string, csrPEM []byte) (certPEM, caPEM []byte, clientID, expiresAt string, err error) {
	req := &EnrollRequest{
		APIKey:        apiKey,
		CSRPEM:        csrPEM,
		DeviceID:      deviceID,
		ClientVersion: "dev",
	}
	resp := &EnrollResponse{}
	err = c.conn.Conn().Invoke(ctx, "/fleet.proxy.v1.EnrollmentService/Enroll", req, resp)
	if err != nil {
		return nil, nil, "", "", fmt.Errorf("enroll RPC: %w", err)
	}
	return resp.ClientCertPEM, resp.CAChainPEM, resp.ClientID, resp.ExpiresAt, nil
}

// Renew requests a new certificate using the existing mTLS identity.
func (c *FleetClient) Renew(ctx context.Context, csrPEM []byte) (certPEM, caPEM []byte, expiresAt string, err error) {
	req := &RenewRequest{CSRPEM: csrPEM}
	resp := &RenewResponse{}
	err = c.conn.Conn().Invoke(ctx, "/fleet.proxy.v1.EnrollmentService/Renew", req, resp)
	if err != nil {
		return nil, nil, "", fmt.Errorf("renew RPC: %w", err)
	}
	return resp.ClientCertPEM, resp.CAChainPEM, resp.ExpiresAt, nil
}

// CreateProject creates a new project in the control plane.
func (c *FleetClient) CreateProject(ctx context.Context, requestID, name, description string) (domain.ProjectSummary, error) {
	req := &CreateProjectRequest{
		RequestID:   requestID,
		Name:        name,
		Description: description,
	}
	resp := &CreateProjectResponse{}
	err := c.conn.Conn().Invoke(ctx, "/fleet.proxy.v1.FleetCommandService/CreateProject", req, resp)
	if err != nil {
		return domain.ProjectSummary{}, fmt.Errorf("create_project RPC: %w", err)
	}
	return domain.ProjectSummary{
		ID:          resp.ProjectID,
		Name:        name,
		Description: description,
	}, nil
}

// CreateEpic creates a new epic under the given project.
func (c *FleetClient) CreateEpic(ctx context.Context, requestID, projectID, title, description string) (domain.EpicSummary, error) {
	req := &CreateEpicRequest{
		RequestID:   requestID,
		ProjectID:   projectID,
		Title:       title,
		Description: description,
	}
	resp := &CreateEpicResponse{}
	err := c.conn.Conn().Invoke(ctx, "/fleet.proxy.v1.FleetCommandService/CreateEpic", req, resp)
	if err != nil {
		return domain.EpicSummary{}, fmt.Errorf("create_epic RPC: %w", err)
	}
	return domain.EpicSummary{
		ID:          resp.EpicID,
		ProjectID:   projectID,
		Title:       title,
		Description: description,
	}, nil
}

// CreateStory creates a new story under the given epic.
func (c *FleetClient) CreateStory(ctx context.Context, requestID, epicID, title, brief string) (domain.StorySummary, error) {
	req := &CreateStoryRequest{
		RequestID: requestID,
		EpicID:    epicID,
		Title:     title,
		Brief:     brief,
	}
	resp := &CreateStoryResponse{}
	err := c.conn.Conn().Invoke(ctx, "/fleet.proxy.v1.FleetCommandService/CreateStory", req, resp)
	if err != nil {
		return domain.StorySummary{}, fmt.Errorf("create_story RPC: %w", err)
	}
	return domain.StorySummary{
		ID:    resp.StoryID,
		EpicID: epicID,
		Title: title,
		Brief: brief,
	}, nil
}

// TransitionStory moves a story to the specified target state.
func (c *FleetClient) TransitionStory(ctx context.Context, storyID, targetState string) error {
	req := &TransitionStoryRequest{StoryID: storyID, TargetState: targetState}
	resp := &TransitionStoryResponse{}
	err := c.conn.Conn().Invoke(ctx, "/fleet.proxy.v1.FleetCommandService/TransitionStory", req, resp)
	if err != nil {
		return fmt.Errorf("transition_story RPC: %w", err)
	}
	if !resp.Success {
		return fmt.Errorf("transition failed: %s", resp.Message)
	}
	return nil
}

// StartCeremony kicks off a ceremony instance for the given story.
func (c *FleetClient) StartCeremony(ctx context.Context, requestID, ceremonyID, definitionName, storyID string, stepIDs []string) (domain.CeremonyStatus, error) {
	req := &StartPlanningCeremonyRequest{
		RequestID:      requestID,
		CeremonyID:     ceremonyID,
		DefinitionName: definitionName,
		StoryID:        storyID,
		StepIDs:        stepIDs,
	}
	resp := &StartPlanningCeremonyResponse{}
	err := c.conn.Conn().Invoke(ctx, "/fleet.proxy.v1.FleetCommandService/StartPlanningCeremony", req, resp)
	if err != nil {
		return domain.CeremonyStatus{}, fmt.Errorf("start_ceremony RPC: %w", err)
	}
	if resp.Status == "FAILED" || resp.Status == "ERROR" {
		return domain.CeremonyStatus{}, fmt.Errorf("start ceremony failed: %s", resp.Message)
	}
	return domain.CeremonyStatus{
		InstanceID: resp.InstanceID,
		Status:     resp.Status,
	}, nil
}

// ListProjects returns all projects visible to the authenticated identity.
func (c *FleetClient) ListProjects(ctx context.Context) ([]domain.ProjectSummary, error) {
	req := &ListProjectsRequest{Limit: 100}
	resp := &ListProjectsResponse{}
	err := c.conn.Conn().Invoke(ctx, "/fleet.proxy.v1.FleetQueryService/ListProjects", req, resp)
	if err != nil {
		return nil, fmt.Errorf("list_projects RPC: %w", err)
	}
	projects := make([]domain.ProjectSummary, 0, len(resp.Projects))
	for _, p := range resp.Projects {
		projects = append(projects, domain.ProjectSummary{
			ID:          p.ProjectID,
			Name:        p.Name,
			Description: p.Description,
			Status:      p.Status,
			Owner:       p.Owner,
			CreatedAt:   p.CreatedAt,
			UpdatedAt:   p.UpdatedAt,
		})
	}
	return projects, nil
}

// ListEpics returns epics belonging to a project with pagination.
func (c *FleetClient) ListEpics(ctx context.Context, projectID string, limit, offset int32) ([]domain.EpicSummary, int32, error) {
	req := &ListEpicsRequest{ProjectID: projectID, Limit: limit, Offset: offset}
	resp := &ListEpicsResponse{}
	err := c.conn.Conn().Invoke(ctx, "/fleet.proxy.v1.FleetQueryService/ListEpics", req, resp)
	if err != nil {
		return nil, 0, fmt.Errorf("list_epics RPC: %w", err)
	}
	epics := make([]domain.EpicSummary, 0, len(resp.Epics))
	for _, e := range resp.Epics {
		epics = append(epics, domain.EpicSummary{
			ID:          e.EpicID,
			ProjectID:   e.ProjectID,
			Title:       e.Title,
			Description: e.Description,
			Status:      e.Status,
			CreatedAt:   e.CreatedAt,
			UpdatedAt:   e.UpdatedAt,
		})
	}
	return epics, resp.TotalCount, nil
}

// ListStories returns stories with optional filtering and pagination.
func (c *FleetClient) ListStories(ctx context.Context, epicID, stateFilter string, limit, offset int32) ([]domain.StorySummary, int32, error) {
	req := &ListStoriesRequest{EpicID: epicID, StateFilter: stateFilter, Limit: limit, Offset: offset}
	resp := &ListStoriesResponse{}
	err := c.conn.Conn().Invoke(ctx, "/fleet.proxy.v1.FleetQueryService/ListStories", req, resp)
	if err != nil {
		return nil, 0, fmt.Errorf("list_stories RPC: %w", err)
	}
	stories := make([]domain.StorySummary, 0, len(resp.Stories))
	for _, s := range resp.Stories {
		stories = append(stories, domain.StorySummary{
			ID:        s.StoryID,
			EpicID:    s.EpicID,
			Title:     s.Title,
			Brief:     s.Brief,
			State:     s.State,
			DorScore:  s.DorScore,
			CreatedBy: s.CreatedBy,
			CreatedAt: s.CreatedAt,
			UpdatedAt: s.UpdatedAt,
		})
	}
	return stories, resp.TotalCount, nil
}

// CreateTask creates a new task under the given story.
func (c *FleetClient) CreateTask(ctx context.Context, requestID, storyID, title, description, taskType, assignedTo string, estimatedHours, priority int32) (domain.TaskSummary, error) {
	req := &CreateTaskRequest{
		RequestID:      requestID,
		StoryID:        storyID,
		Title:          title,
		Description:    description,
		Type:           taskType,
		AssignedTo:     assignedTo,
		EstimatedHours: estimatedHours,
		Priority:       priority,
	}
	resp := &CreateTaskResponse{}
	err := c.conn.Conn().Invoke(ctx, "/fleet.proxy.v1.FleetCommandService/CreateTask", req, resp)
	if err != nil {
		return domain.TaskSummary{}, fmt.Errorf("create_task RPC: %w", err)
	}
	return domain.TaskSummary{
		ID:             resp.TaskID,
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
	req := &ListTasksRequest{StoryID: storyID, StatusFilter: statusFilter, Limit: limit, Offset: offset}
	resp := &ListTasksResponse{}
	err := c.conn.Conn().Invoke(ctx, "/fleet.proxy.v1.FleetQueryService/ListTasks", req, resp)
	if err != nil {
		return nil, 0, fmt.Errorf("list_tasks RPC: %w", err)
	}
	tasks := make([]domain.TaskSummary, 0, len(resp.Tasks))
	for _, t := range resp.Tasks {
		tasks = append(tasks, domain.TaskSummary{
			ID:             t.TaskID,
			StoryID:        t.StoryID,
			Title:          t.Title,
			Description:    t.Description,
			Type:           t.Type,
			Status:         t.Status,
			AssignedTo:     t.AssignedTo,
			EstimatedHours: t.EstimatedHours,
			Priority:       t.Priority,
			CreatedAt:      t.CreatedAt,
			UpdatedAt:      t.UpdatedAt,
		})
	}
	return tasks, resp.TotalCount, nil
}

// ListCeremonies returns ceremony instances with optional filtering and pagination.
func (c *FleetClient) ListCeremonies(ctx context.Context, ceremonyID, statusFilter string, limit, offset int32) ([]domain.CeremonyStatus, int32, error) {
	req := &ListCeremonyInstancesRequest{
		StateFilter: statusFilter,
		StoryID:     ceremonyID,
		Limit:       limit,
		Offset:      offset,
	}
	resp := &ListCeremonyInstancesResponse{}
	err := c.conn.Conn().Invoke(ctx, "/fleet.proxy.v1.FleetQueryService/ListCeremonyInstances", req, resp)
	if err != nil {
		return nil, 0, fmt.Errorf("list_ceremony_instances RPC: %w", err)
	}
	ceremonies := make([]domain.CeremonyStatus, 0, len(resp.Ceremonies))
	for _, cm := range resp.Ceremonies {
		ceremonies = append(ceremonies, ceremonyMsgToDomain(cm))
	}
	return ceremonies, resp.TotalCount, nil
}

// GetCeremony returns the current status of a ceremony instance.
func (c *FleetClient) GetCeremony(ctx context.Context, instanceID string) (domain.CeremonyStatus, error) {
	req := &GetCeremonyInstanceRequest{InstanceID: instanceID}
	resp := &CeremonyInstanceResponse{}
	err := c.conn.Conn().Invoke(ctx, "/fleet.proxy.v1.FleetQueryService/GetCeremonyInstance", req, resp)
	if err != nil {
		return domain.CeremonyStatus{}, fmt.Errorf("get_ceremony_instance RPC: %w", err)
	}
	return ceremonyMsgToDomain(resp.Ceremony), nil
}

func ceremonyMsgToDomain(m *CeremonyInstanceMsg) domain.CeremonyStatus {
	if m == nil {
		return domain.CeremonyStatus{}
	}
	return domain.CeremonyStatus{
		InstanceID:     m.InstanceID,
		CeremonyID:     m.CeremonyID,
		StoryID:        m.StoryID,
		DefinitionName: m.DefinitionName,
		CurrentState:   m.CurrentState,
		Status:         m.Status,
		CorrelationID:  m.CorrelationID,
		StepStatuses:   m.StepStatus,
		StepOutputs:    m.StepOutputs,
		CreatedAt:      m.CreatedAt,
		UpdatedAt:      m.UpdatedAt,
	}
}

// ApproveDecision approves a pending decision for the given story.
func (c *FleetClient) ApproveDecision(ctx context.Context, storyID, decisionID, comment string) error {
	req := &ApproveDecisionRequest{StoryID: storyID, DecisionID: decisionID, Comment: comment}
	resp := &ApproveDecisionResponse{}
	err := c.conn.Conn().Invoke(ctx, "/fleet.proxy.v1.FleetCommandService/ApproveDecision", req, resp)
	if err != nil {
		return fmt.Errorf("approve_decision RPC: %w", err)
	}
	if !resp.Success {
		return fmt.Errorf("approve decision failed: %s", resp.Message)
	}
	return nil
}

// RejectDecision rejects a pending decision for the given story.
func (c *FleetClient) RejectDecision(ctx context.Context, storyID, decisionID, reason string) error {
	req := &RejectDecisionRequest{StoryID: storyID, DecisionID: decisionID, Reason: reason}
	resp := &RejectDecisionResponse{}
	err := c.conn.Conn().Invoke(ctx, "/fleet.proxy.v1.FleetCommandService/RejectDecision", req, resp)
	if err != nil {
		return fmt.Errorf("reject_decision RPC: %w", err)
	}
	if !resp.Success {
		return fmt.Errorf("reject decision failed: %s", resp.Message)
	}
	return nil
}

// CreateBacklogReview creates a new backlog review ceremony.
func (c *FleetClient) CreateBacklogReview(ctx context.Context, requestID string, storyIDs []string) (domain.BacklogReview, error) {
	req := &CreateBacklogReviewRequest{RequestID: requestID, StoryIDs: storyIDs}
	resp := &CreateBacklogReviewResponse{}
	if err := c.conn.Conn().Invoke(ctx, "/fleet.proxy.v1.FleetCommandService/CreateBacklogReview", req, resp); err != nil {
		return domain.BacklogReview{}, fmt.Errorf("create_backlog_review RPC: %w", err)
	}
	return backlogReviewMsgToDomain(resp.Ceremony), nil
}

// StartBacklogReview starts a backlog review ceremony.
func (c *FleetClient) StartBacklogReview(ctx context.Context, requestID, ceremonyID string) (domain.BacklogReview, int32, error) {
	req := &StartBacklogReviewRequest{RequestID: requestID, CeremonyID: ceremonyID}
	resp := &StartBacklogReviewResponse{}
	if err := c.conn.Conn().Invoke(ctx, "/fleet.proxy.v1.FleetCommandService/StartBacklogReview", req, resp); err != nil {
		return domain.BacklogReview{}, 0, fmt.Errorf("start_backlog_review RPC: %w", err)
	}
	return backlogReviewMsgToDomain(resp.Ceremony), resp.TotalDeliberationsSubmitted, nil
}

// GetBacklogReview fetches a single backlog review ceremony.
func (c *FleetClient) GetBacklogReview(ctx context.Context, ceremonyID string) (domain.BacklogReview, error) {
	req := &GetBacklogReviewProxyRequest{CeremonyID: ceremonyID}
	resp := &GetBacklogReviewProxyResponse{}
	if err := c.conn.Conn().Invoke(ctx, "/fleet.proxy.v1.FleetQueryService/GetBacklogReview", req, resp); err != nil {
		return domain.BacklogReview{}, fmt.Errorf("get_backlog_review RPC: %w", err)
	}
	return backlogReviewMsgToDomain(resp.Ceremony), nil
}

// ListBacklogReviews returns backlog review ceremonies with filtering.
func (c *FleetClient) ListBacklogReviews(ctx context.Context, statusFilter string, limit, offset int32) ([]domain.BacklogReview, int32, error) {
	req := &ListBacklogReviewsProxyRequest{StatusFilter: statusFilter, Limit: limit, Offset: offset}
	resp := &ListBacklogReviewsProxyResponse{}
	if err := c.conn.Conn().Invoke(ctx, "/fleet.proxy.v1.FleetQueryService/ListBacklogReviews", req, resp); err != nil {
		return nil, 0, fmt.Errorf("list_backlog_reviews RPC: %w", err)
	}
	reviews := make([]domain.BacklogReview, 0, len(resp.Ceremonies))
	for _, cer := range resp.Ceremonies {
		reviews = append(reviews, backlogReviewMsgToDomain(cer))
	}
	return reviews, resp.TotalCount, nil
}

// ApproveReviewPlan approves a story's review plan.
func (c *FleetClient) ApproveReviewPlan(ctx context.Context, ceremonyID, storyID, poNotes, poConcerns, priorityAdj, prioReason string) (domain.BacklogReview, string, error) {
	req := &ApproveReviewPlanProxyRequest{
		CeremonyID: ceremonyID, StoryID: storyID, PONotes: poNotes,
		POConcerns: poConcerns, PriorityAdjustment: priorityAdj, POPriorityReason: prioReason,
	}
	resp := &ApproveReviewPlanProxyResponse{}
	if err := c.conn.Conn().Invoke(ctx, "/fleet.proxy.v1.FleetCommandService/ApproveReviewPlan", req, resp); err != nil {
		return domain.BacklogReview{}, "", fmt.Errorf("approve_review_plan RPC: %w", err)
	}
	return backlogReviewMsgToDomain(resp.Ceremony), resp.PlanID, nil
}

// RejectReviewPlan rejects a story's review plan.
func (c *FleetClient) RejectReviewPlan(ctx context.Context, ceremonyID, storyID, reason string) (domain.BacklogReview, error) {
	req := &RejectReviewPlanProxyRequest{CeremonyID: ceremonyID, StoryID: storyID, Reason: reason}
	resp := &RejectReviewPlanProxyResponse{}
	if err := c.conn.Conn().Invoke(ctx, "/fleet.proxy.v1.FleetCommandService/RejectReviewPlan", req, resp); err != nil {
		return domain.BacklogReview{}, fmt.Errorf("reject_review_plan RPC: %w", err)
	}
	return backlogReviewMsgToDomain(resp.Ceremony), nil
}

// CompleteBacklogReview marks a backlog review ceremony as completed.
func (c *FleetClient) CompleteBacklogReview(ctx context.Context, ceremonyID string) (domain.BacklogReview, error) {
	req := &CompleteBacklogReviewRequest{CeremonyID: ceremonyID}
	resp := &CompleteBacklogReviewResponse{}
	if err := c.conn.Conn().Invoke(ctx, "/fleet.proxy.v1.FleetCommandService/CompleteBacklogReview", req, resp); err != nil {
		return domain.BacklogReview{}, fmt.Errorf("complete_backlog_review RPC: %w", err)
	}
	return backlogReviewMsgToDomain(resp.Ceremony), nil
}

// CancelBacklogReview cancels a backlog review ceremony.
func (c *FleetClient) CancelBacklogReview(ctx context.Context, ceremonyID string) (domain.BacklogReview, error) {
	req := &CancelBacklogReviewRequest{CeremonyID: ceremonyID}
	resp := &CancelBacklogReviewResponse{}
	if err := c.conn.Conn().Invoke(ctx, "/fleet.proxy.v1.FleetCommandService/CancelBacklogReview", req, resp); err != nil {
		return domain.BacklogReview{}, fmt.Errorf("cancel_backlog_review RPC: %w", err)
	}
	return backlogReviewMsgToDomain(resp.Ceremony), nil
}

func backlogReviewMsgToDomain(m *BacklogReviewMsgWire) domain.BacklogReview {
	if m == nil {
		return domain.BacklogReview{}
	}
	results := make([]domain.StoryReviewResult, 0, len(m.ReviewResults))
	for _, r := range m.ReviewResults {
		var pp domain.PlanPreliminary
		if r.PlanPreliminary != nil {
			pp = domain.PlanPreliminary{
				Title:               r.PlanPreliminary.Title,
				Description:         r.PlanPreliminary.Description,
				TechnicalNotes:      r.PlanPreliminary.TechnicalNotes,
				EstimatedComplexity: r.PlanPreliminary.EstimatedComplexity,
				AcceptanceCriteria:  r.PlanPreliminary.AcceptanceCriteria,
				Roles:               r.PlanPreliminary.Roles,
				Dependencies:        r.PlanPreliminary.Dependencies,
				TasksOutline:        r.PlanPreliminary.TasksOutline,
			}
		}
		results = append(results, domain.StoryReviewResult{
			StoryID:            r.StoryID,
			ArchitectFeedback:  r.ArchitectFeedback,
			QAFeedback:         r.QAFeedback,
			DevopsFeedback:     r.DevopsFeedback,
			ApprovalStatus:     r.ApprovalStatus,
			ReviewedAt:         r.ReviewedAt,
			ApprovedBy:         r.ApprovedBy,
			ApprovedAt:         r.ApprovedAt,
			RejectedBy:         r.RejectedBy,
			RejectedAt:         r.RejectedAt,
			RejectionReason:    r.RejectionReason,
			PONotes:            r.PONotes,
			POConcerns:         r.POConcerns,
			PriorityAdjustment: r.PriorityAdjustment,
			POPriorityReason:   r.POPriorityReason,
			PlanID:             r.PlanID,
			Recommendations:    r.Recommendations,
			PlanPreliminary:    pp,
		})
	}
	return domain.BacklogReview{
		CeremonyID:    m.CeremonyID,
		Status:        m.Status,
		CreatedBy:     m.CreatedBy,
		CreatedAt:     m.CreatedAt,
		UpdatedAt:     m.UpdatedAt,
		StartedAt:     m.StartedAt,
		CompletedAt:   m.CompletedAt,
		StoryIDs:      m.StoryIDs,
		ReviewResults: results,
	}
}

// Close releases the underlying gRPC connection.
func (c *FleetClient) Close() error {
	return c.conn.Close()
}
