// Package planning provides an adapter implementing ports.PlanningClient
// over gRPC, targeting the upstream fleet.planning.v2.PlanningService.
package planning

import (
	"context"
	"fmt"
	"log/slog"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"

	pb "github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/gen/planningv2"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

// Client is the planning service gRPC adapter.
type Client struct {
	conn *grpc.ClientConn
	rpc  pb.PlanningServiceClient
}

// NewClient dials the upstream planning service and returns a ready Client.
// Uses insecure transport (service runs inside the cluster mesh).
func NewClient(addr string) (*Client, error) {
	conn, err := grpc.NewClient(addr, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		return nil, fmt.Errorf("dial planning service %s: %w", addr, err)
	}
	slog.Info("planning client connected", "addr", addr)
	return &Client{conn: conn, rpc: pb.NewPlanningServiceClient(conn)}, nil
}

// Close releases the underlying gRPC connection.
func (c *Client) Close() error {
	return c.conn.Close()
}

// ---------------------------------------------------------------------------
// Command methods
// ---------------------------------------------------------------------------

func (c *Client) CreateProject(ctx context.Context, name, description, createdBy string) (string, error) {
	resp, err := c.rpc.CreateProject(ctx, &pb.CreateProjectRequest{
		Name:        name,
		Description: description,
		Owner:       createdBy,
	})
	if err != nil {
		return "", fmt.Errorf("CreateProject RPC: %w", err)
	}
	if resp.GetProject() == nil {
		return "", fmt.Errorf("CreateProject: nil project in response")
	}
	return resp.GetProject().GetProjectId(), nil
}

func (c *Client) CreateEpic(ctx context.Context, projectID, title, description string) (string, error) {
	resp, err := c.rpc.CreateEpic(ctx, &pb.CreateEpicRequest{
		ProjectId:   projectID,
		Title:       title,
		Description: description,
	})
	if err != nil {
		return "", fmt.Errorf("CreateEpic RPC: %w", err)
	}
	if resp.GetEpic() == nil {
		return "", fmt.Errorf("CreateEpic: nil epic in response")
	}
	return resp.GetEpic().GetEpicId(), nil
}

func (c *Client) CreateStory(ctx context.Context, epicID, title, brief, createdBy string) (string, error) {
	resp, err := c.rpc.CreateStory(ctx, &pb.CreateStoryRequest{
		EpicId:    epicID,
		Title:     title,
		Brief:     brief,
		CreatedBy: createdBy,
	})
	if err != nil {
		return "", fmt.Errorf("CreateStory RPC: %w", err)
	}
	if resp.GetStory() == nil {
		return "", fmt.Errorf("CreateStory: nil story in response")
	}
	return resp.GetStory().GetStoryId(), nil
}

func (c *Client) TransitionStory(ctx context.Context, storyID, targetState string) error {
	_, err := c.rpc.TransitionStory(ctx, &pb.TransitionStoryRequest{
		StoryId:     storyID,
		TargetState: targetState,
	})
	if err != nil {
		return fmt.Errorf("TransitionStory RPC: %w", err)
	}
	return nil
}

func (c *Client) CreateTask(ctx context.Context, requestID, storyID, title, description, taskType, assignedTo string, estimatedHours, priority int32) (string, error) {
	resp, err := c.rpc.CreateTask(ctx, &pb.CreateTaskRequest{
		StoryId:        storyID,
		Title:          title,
		Description:    description,
		Type:           taskType,
		AssignedTo:     assignedTo,
		EstimatedHours: estimatedHours,
		Priority:       priority,
		RequestId:      requestID,
	})
	if err != nil {
		return "", fmt.Errorf("CreateTask RPC: %w", err)
	}
	if resp.GetTask() == nil {
		return "", fmt.Errorf("CreateTask: nil task in response")
	}
	return resp.GetTask().GetTaskId(), nil
}

func (c *Client) ApproveDecision(ctx context.Context, storyID, decisionID, approvedBy, comment string) error {
	_, err := c.rpc.ApproveDecision(ctx, &pb.ApproveDecisionRequest{
		StoryId:    storyID,
		DecisionId: decisionID,
		ApprovedBy: approvedBy,
		Comment:    &comment,
	})
	if err != nil {
		return fmt.Errorf("ApproveDecision RPC: %w", err)
	}
	return nil
}

func (c *Client) RejectDecision(ctx context.Context, storyID, decisionID, rejectedBy, reason string) error {
	_, err := c.rpc.RejectDecision(ctx, &pb.RejectDecisionRequest{
		StoryId:    storyID,
		DecisionId: decisionID,
		RejectedBy: rejectedBy,
		Reason:     reason,
	})
	if err != nil {
		return fmt.Errorf("RejectDecision RPC: %w", err)
	}
	return nil
}

// ---------------------------------------------------------------------------
// Query methods
// ---------------------------------------------------------------------------

func (c *Client) ListProjects(ctx context.Context, statusFilter string, limit, offset int32) ([]ports.ProjectResult, int32, error) {
	resp, err := c.rpc.ListProjects(ctx, &pb.ListProjectsRequest{
		StatusFilter: &statusFilter,
		Limit:        limit,
		Offset:       offset,
	})
	if err != nil {
		return nil, 0, fmt.Errorf("ListProjects RPC: %w", err)
	}
	out := make([]ports.ProjectResult, len(resp.GetProjects()))
	for i, p := range resp.GetProjects() {
		out[i] = ports.ProjectResult{
			ProjectID:   p.GetProjectId(),
			Name:        p.GetName(),
			Description: p.GetDescription(),
			Status:      p.GetStatus(),
			Owner:       p.GetOwner(),
			CreatedAt:   p.GetCreatedAt(),
			UpdatedAt:   p.GetUpdatedAt(),
		}
	}
	return out, resp.GetTotalCount(), nil
}

func (c *Client) ListEpics(ctx context.Context, projectID, statusFilter string, limit, offset int32) ([]ports.EpicResult, int32, error) {
	resp, err := c.rpc.ListEpics(ctx, &pb.ListEpicsRequest{
		ProjectId:    &projectID,
		StatusFilter: &statusFilter,
		Limit:        limit,
		Offset:       offset,
	})
	if err != nil {
		return nil, 0, fmt.Errorf("ListEpics RPC: %w", err)
	}
	out := make([]ports.EpicResult, len(resp.GetEpics()))
	for i, e := range resp.GetEpics() {
		out[i] = ports.EpicResult{
			EpicID:      e.GetEpicId(),
			ProjectID:   e.GetProjectId(),
			Title:       e.GetTitle(),
			Description: e.GetDescription(),
			Status:      e.GetStatus(),
			CreatedAt:   e.GetCreatedAt(),
			UpdatedAt:   e.GetUpdatedAt(),
		}
	}
	return out, resp.GetTotalCount(), nil
}

func (c *Client) ListStories(ctx context.Context, epicID, stateFilter string, limit, offset int32) ([]ports.StoryResult, int32, error) {
	resp, err := c.rpc.ListStories(ctx, &pb.ListStoriesRequest{
		EpicId:      &epicID,
		StateFilter: &stateFilter,
		Limit:       limit,
		Offset:      offset,
	})
	if err != nil {
		return nil, 0, fmt.Errorf("ListStories RPC: %w", err)
	}
	out := make([]ports.StoryResult, len(resp.GetStories()))
	for i, s := range resp.GetStories() {
		out[i] = ports.StoryResult{
			StoryID:   s.GetStoryId(),
			EpicID:    s.GetEpicId(),
			Title:     s.GetTitle(),
			Brief:     s.GetBrief(),
			State:     s.GetState(),
			DorScore:  s.GetDorScore(),
			CreatedBy: s.GetCreatedBy(),
			CreatedAt: s.GetCreatedAt(),
			UpdatedAt: s.GetUpdatedAt(),
		}
	}
	return out, resp.GetTotalCount(), nil
}

func (c *Client) CreateBacklogReview(ctx context.Context, createdBy string, storyIDs []string) (ports.BacklogReviewResult, error) {
	resp, err := c.rpc.CreateBacklogReviewCeremony(ctx, &pb.CreateBacklogReviewCeremonyRequest{
		CreatedBy: createdBy,
		StoryIds:  storyIDs,
	})
	if err != nil {
		return ports.BacklogReviewResult{}, fmt.Errorf("CreateBacklogReviewCeremony RPC: %w", err)
	}
	return backlogReviewToResult(resp.GetCeremony()), nil
}

func (c *Client) StartBacklogReview(ctx context.Context, ceremonyID, startedBy string) (ports.BacklogReviewResult, int32, error) {
	resp, err := c.rpc.StartBacklogReviewCeremony(ctx, &pb.StartBacklogReviewCeremonyRequest{
		CeremonyId: ceremonyID,
		StartedBy:  startedBy,
	})
	if err != nil {
		return ports.BacklogReviewResult{}, 0, fmt.Errorf("StartBacklogReviewCeremony RPC: %w", err)
	}
	return backlogReviewToResult(resp.GetCeremony()), resp.GetTotalDeliberationsSubmitted(), nil
}

func (c *Client) GetBacklogReview(ctx context.Context, ceremonyID string) (ports.BacklogReviewResult, error) {
	resp, err := c.rpc.GetBacklogReviewCeremony(ctx, &pb.GetBacklogReviewCeremonyRequest{
		CeremonyId: ceremonyID,
	})
	if err != nil {
		return ports.BacklogReviewResult{}, fmt.Errorf("GetBacklogReviewCeremony RPC: %w", err)
	}
	return backlogReviewToResult(resp.GetCeremony()), nil
}

func (c *Client) ListBacklogReviews(ctx context.Context, statusFilter string, limit, offset int32) ([]ports.BacklogReviewResult, int32, error) {
	req := &pb.ListBacklogReviewCeremoniesRequest{
		Limit:  limit,
		Offset: offset,
	}
	if statusFilter != "" {
		req.StatusFilter = &statusFilter
	}
	resp, err := c.rpc.ListBacklogReviewCeremonies(ctx, req)
	if err != nil {
		return nil, 0, fmt.Errorf("ListBacklogReviewCeremonies RPC: %w", err)
	}
	out := make([]ports.BacklogReviewResult, len(resp.GetCeremonies()))
	for i, cer := range resp.GetCeremonies() {
		out[i] = backlogReviewToResult(cer)
	}
	return out, resp.GetTotalCount(), nil
}

func (c *Client) ApproveReviewPlan(ctx context.Context, ceremonyID, storyID, approvedBy, poNotes, poConcerns, priorityAdj, prioReason string) (ports.BacklogReviewResult, string, error) {
	req := &pb.ApproveReviewPlanRequest{
		CeremonyId: ceremonyID,
		StoryId:    storyID,
		ApprovedBy: approvedBy,
		PoNotes:    poNotes,
	}
	if poConcerns != "" {
		req.PoConcerns = &poConcerns
	}
	if priorityAdj != "" {
		req.PriorityAdjustment = &priorityAdj
	}
	if prioReason != "" {
		req.PoPriorityReason = &prioReason
	}
	resp, err := c.rpc.ApproveReviewPlan(ctx, req)
	if err != nil {
		return ports.BacklogReviewResult{}, "", fmt.Errorf("ApproveReviewPlan RPC: %w", err)
	}
	return backlogReviewToResult(resp.GetCeremony()), resp.GetPlanId(), nil
}

func (c *Client) RejectReviewPlan(ctx context.Context, ceremonyID, storyID, rejectedBy, reason string) (ports.BacklogReviewResult, error) {
	resp, err := c.rpc.RejectReviewPlan(ctx, &pb.RejectReviewPlanRequest{
		CeremonyId:      ceremonyID,
		StoryId:         storyID,
		RejectedBy:      rejectedBy,
		RejectionReason: reason,
	})
	if err != nil {
		return ports.BacklogReviewResult{}, fmt.Errorf("RejectReviewPlan RPC: %w", err)
	}
	return backlogReviewToResult(resp.GetCeremony()), nil
}

func (c *Client) CompleteBacklogReview(ctx context.Context, ceremonyID, completedBy string) (ports.BacklogReviewResult, error) {
	resp, err := c.rpc.CompleteBacklogReviewCeremony(ctx, &pb.CompleteBacklogReviewCeremonyRequest{
		CeremonyId:  ceremonyID,
		CompletedBy: completedBy,
	})
	if err != nil {
		return ports.BacklogReviewResult{}, fmt.Errorf("CompleteBacklogReviewCeremony RPC: %w", err)
	}
	return backlogReviewToResult(resp.GetCeremony()), nil
}

func (c *Client) CancelBacklogReview(ctx context.Context, ceremonyID, cancelledBy string) (ports.BacklogReviewResult, error) {
	resp, err := c.rpc.CancelBacklogReviewCeremony(ctx, &pb.CancelBacklogReviewCeremonyRequest{
		CeremonyId:  ceremonyID,
		CancelledBy: cancelledBy,
	})
	if err != nil {
		return ports.BacklogReviewResult{}, fmt.Errorf("CancelBacklogReviewCeremony RPC: %w", err)
	}
	return backlogReviewToResult(resp.GetCeremony()), nil
}

// ---------------------------------------------------------------------------
// Backlog review converters
// ---------------------------------------------------------------------------

func backlogReviewToResult(c *pb.BacklogReviewCeremony) ports.BacklogReviewResult {
	if c == nil {
		return ports.BacklogReviewResult{}
	}
	results := make([]ports.StoryReviewResultItem, len(c.GetReviewResults()))
	for i, r := range c.GetReviewResults() {
		results[i] = storyReviewToItem(r)
	}
	return ports.BacklogReviewResult{
		CeremonyID:    c.GetCeremonyId(),
		Status:        c.GetStatus(),
		CreatedBy:     c.GetCreatedBy(),
		CreatedAt:     c.GetCreatedAt(),
		UpdatedAt:     c.GetUpdatedAt(),
		StartedAt:     c.GetStartedAt(),
		CompletedAt:   c.GetCompletedAt(),
		StoryIDs:      c.GetStoryIds(),
		ReviewResults: results,
	}
}

func storyReviewToItem(r *pb.StoryReviewResult) ports.StoryReviewResultItem {
	if r == nil {
		return ports.StoryReviewResultItem{}
	}
	return ports.StoryReviewResultItem{
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
		PlanPreliminary:    planPreliminaryToResult(r.GetPlanPreliminary()),
	}
}

func planPreliminaryToResult(p *pb.PlanPreliminary) ports.PlanPreliminaryResult {
	if p == nil {
		return ports.PlanPreliminaryResult{}
	}
	return ports.PlanPreliminaryResult{
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

func (c *Client) ListTasks(ctx context.Context, storyID, statusFilter string, limit, offset int32) ([]ports.TaskResult, int32, error) {
	resp, err := c.rpc.ListTasks(ctx, &pb.ListTasksRequest{
		StoryId:      &storyID,
		StatusFilter: &statusFilter,
		Limit:        limit,
		Offset:       offset,
	})
	if err != nil {
		return nil, 0, fmt.Errorf("ListTasks RPC: %w", err)
	}
	out := make([]ports.TaskResult, len(resp.GetTasks()))
	for i, t := range resp.GetTasks() {
		out[i] = ports.TaskResult{
			TaskID:         t.GetTaskId(),
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
		}
	}
	return out, resp.GetTotalCount(), nil
}
