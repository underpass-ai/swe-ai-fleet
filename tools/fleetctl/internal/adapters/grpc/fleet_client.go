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
	return nil, nil, "", fmt.Errorf("not implemented: awaiting proto generation")
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
	return fmt.Errorf("not implemented: awaiting proto generation")
}

// StartCeremony kicks off a ceremony instance for the given story.
func (c *FleetClient) StartCeremony(ctx context.Context, requestID, ceremonyID, definitionName, storyID string, stepIDs []string) (domain.CeremonyStatus, error) {
	return domain.CeremonyStatus{}, fmt.Errorf("not implemented: awaiting proto generation")
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
	return nil, 0, fmt.Errorf("not implemented: awaiting proto generation")
}

// GetCeremony returns the current status of a ceremony instance.
func (c *FleetClient) GetCeremony(ctx context.Context, instanceID string) (domain.CeremonyStatus, error) {
	return domain.CeremonyStatus{}, fmt.Errorf("not implemented: awaiting proto generation")
}

// ApproveDecision approves a pending decision for the given story.
func (c *FleetClient) ApproveDecision(ctx context.Context, storyID, decisionID, comment string) error {
	return fmt.Errorf("not implemented: awaiting proto generation")
}

// RejectDecision rejects a pending decision for the given story.
func (c *FleetClient) RejectDecision(ctx context.Context, storyID, decisionID, reason string) error {
	return fmt.Errorf("not implemented: awaiting proto generation")
}

// Close releases the underlying gRPC connection.
func (c *FleetClient) Close() error {
	return c.conn.Close()
}
