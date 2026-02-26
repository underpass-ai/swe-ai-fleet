package grpcapi

import (
	"context"
	"fmt"
	"log/slog"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/query"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/event"
)

// ---------------------------------------------------------------------------
// Request / Response types matching fleet.proxy.v1.FleetQueryService proto.
// ---------------------------------------------------------------------------

// ListProjectsRequest mirrors fleet.proxy.v1.ListProjectsRequest.
type ListProjectsRequest struct {
	StatusFilter string `protobuf:"bytes,1,opt,name=status_filter,json=statusFilter" json:"status_filter,omitempty"`
	Limit        int32  `protobuf:"varint,2,opt,name=limit" json:"limit,omitempty"`
	Offset       int32  `protobuf:"varint,3,opt,name=offset" json:"offset,omitempty"`
}

func (m *ListProjectsRequest) Reset()         { *m = ListProjectsRequest{} }
func (m *ListProjectsRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *ListProjectsRequest) ProtoMessage()  {}

// ListProjectsResponse mirrors fleet.proxy.v1.ListProjectsResponse.
type ListProjectsResponse struct {
	Projects   []*ProjectMsg `protobuf:"bytes,1,rep,name=projects" json:"projects,omitempty"`
	TotalCount int32         `protobuf:"varint,2,opt,name=total_count,json=totalCount" json:"total_count,omitempty"`
}

func (m *ListProjectsResponse) Reset()         { *m = ListProjectsResponse{} }
func (m *ListProjectsResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *ListProjectsResponse) ProtoMessage()  {}

// ProjectMsg mirrors fleet.proxy.v1.Project.
type ProjectMsg struct {
	ProjectID   string `protobuf:"bytes,1,opt,name=project_id,json=projectId" json:"project_id,omitempty"`
	Name        string `protobuf:"bytes,2,opt,name=name" json:"name,omitempty"`
	Description string `protobuf:"bytes,3,opt,name=description" json:"description,omitempty"`
	Status      string `protobuf:"bytes,4,opt,name=status" json:"status,omitempty"`
	Owner       string `protobuf:"bytes,5,opt,name=owner" json:"owner,omitempty"`
	CreatedAt   string `protobuf:"bytes,6,opt,name=created_at,json=createdAt" json:"created_at,omitempty"`
	UpdatedAt   string `protobuf:"bytes,7,opt,name=updated_at,json=updatedAt" json:"updated_at,omitempty"`
}

func (m *ProjectMsg) Reset()         { *m = ProjectMsg{} }
func (m *ProjectMsg) String() string { return fmt.Sprintf("%+v", *m) }
func (m *ProjectMsg) ProtoMessage()  {}

// ListEpicsRequest mirrors fleet.proxy.v1.ListEpicsRequest.
type ListEpicsRequest struct {
	ProjectID    string `protobuf:"bytes,1,opt,name=project_id,json=projectId" json:"project_id,omitempty"`
	StatusFilter string `protobuf:"bytes,2,opt,name=status_filter,json=statusFilter" json:"status_filter,omitempty"`
	Limit        int32  `protobuf:"varint,3,opt,name=limit" json:"limit,omitempty"`
	Offset       int32  `protobuf:"varint,4,opt,name=offset" json:"offset,omitempty"`
}

func (m *ListEpicsRequest) Reset()         { *m = ListEpicsRequest{} }
func (m *ListEpicsRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *ListEpicsRequest) ProtoMessage()  {}

// ListEpicsResponse mirrors fleet.proxy.v1.ListEpicsResponse.
type ListEpicsResponse struct {
	Epics      []*EpicMsg `protobuf:"bytes,1,rep,name=epics" json:"epics,omitempty"`
	TotalCount int32      `protobuf:"varint,2,opt,name=total_count,json=totalCount" json:"total_count,omitempty"`
}

func (m *ListEpicsResponse) Reset()         { *m = ListEpicsResponse{} }
func (m *ListEpicsResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *ListEpicsResponse) ProtoMessage()  {}

// EpicMsg mirrors fleet.proxy.v1.Epic.
type EpicMsg struct {
	EpicID      string `protobuf:"bytes,1,opt,name=epic_id,json=epicId" json:"epic_id,omitempty"`
	ProjectID   string `protobuf:"bytes,2,opt,name=project_id,json=projectId" json:"project_id,omitempty"`
	Title       string `protobuf:"bytes,3,opt,name=title" json:"title,omitempty"`
	Description string `protobuf:"bytes,4,opt,name=description" json:"description,omitempty"`
	Status      string `protobuf:"bytes,5,opt,name=status" json:"status,omitempty"`
	CreatedAt   string `protobuf:"bytes,6,opt,name=created_at,json=createdAt" json:"created_at,omitempty"`
	UpdatedAt   string `protobuf:"bytes,7,opt,name=updated_at,json=updatedAt" json:"updated_at,omitempty"`
}

func (m *EpicMsg) Reset()         { *m = EpicMsg{} }
func (m *EpicMsg) String() string { return fmt.Sprintf("%+v", *m) }
func (m *EpicMsg) ProtoMessage()  {}

// ListStoriesRequest mirrors fleet.proxy.v1.ListStoriesRequest.
type ListStoriesRequest struct {
	EpicID      string `protobuf:"bytes,1,opt,name=epic_id,json=epicId" json:"epic_id,omitempty"`
	StateFilter string `protobuf:"bytes,2,opt,name=state_filter,json=stateFilter" json:"state_filter,omitempty"`
	Limit       int32  `protobuf:"varint,3,opt,name=limit" json:"limit,omitempty"`
	Offset      int32  `protobuf:"varint,4,opt,name=offset" json:"offset,omitempty"`
}

func (m *ListStoriesRequest) Reset()         { *m = ListStoriesRequest{} }
func (m *ListStoriesRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *ListStoriesRequest) ProtoMessage()  {}

// ListStoriesResponse mirrors fleet.proxy.v1.ListStoriesResponse.
type ListStoriesResponse struct {
	Stories    []*StoryMsg `protobuf:"bytes,1,rep,name=stories" json:"stories,omitempty"`
	TotalCount int32       `protobuf:"varint,2,opt,name=total_count,json=totalCount" json:"total_count,omitempty"`
}

func (m *ListStoriesResponse) Reset()         { *m = ListStoriesResponse{} }
func (m *ListStoriesResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *ListStoriesResponse) ProtoMessage()  {}

// StoryMsg mirrors fleet.proxy.v1.Story.
type StoryMsg struct {
	StoryID   string `protobuf:"bytes,1,opt,name=story_id,json=storyId" json:"story_id,omitempty"`
	EpicID    string `protobuf:"bytes,2,opt,name=epic_id,json=epicId" json:"epic_id,omitempty"`
	Title     string `protobuf:"bytes,3,opt,name=title" json:"title,omitempty"`
	Brief     string `protobuf:"bytes,4,opt,name=brief" json:"brief,omitempty"`
	State     string `protobuf:"bytes,5,opt,name=state" json:"state,omitempty"`
	DorScore  int32  `protobuf:"varint,6,opt,name=dor_score,json=dorScore" json:"dor_score,omitempty"`
	CreatedBy string `protobuf:"bytes,7,opt,name=created_by,json=createdBy" json:"created_by,omitempty"`
	CreatedAt string `protobuf:"bytes,8,opt,name=created_at,json=createdAt" json:"created_at,omitempty"`
	UpdatedAt string `protobuf:"bytes,9,opt,name=updated_at,json=updatedAt" json:"updated_at,omitempty"`
}

func (m *StoryMsg) Reset()         { *m = StoryMsg{} }
func (m *StoryMsg) String() string { return fmt.Sprintf("%+v", *m) }
func (m *StoryMsg) ProtoMessage()  {}

// ListTasksRequest mirrors fleet.proxy.v1.ListTasksRequest.
type ListTasksRequest struct {
	StoryID      string `protobuf:"bytes,1,opt,name=story_id,json=storyId" json:"story_id,omitempty"`
	StatusFilter string `protobuf:"bytes,2,opt,name=status_filter,json=statusFilter" json:"status_filter,omitempty"`
	Limit        int32  `protobuf:"varint,3,opt,name=limit" json:"limit,omitempty"`
	Offset       int32  `protobuf:"varint,4,opt,name=offset" json:"offset,omitempty"`
}

func (m *ListTasksRequest) Reset()         { *m = ListTasksRequest{} }
func (m *ListTasksRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *ListTasksRequest) ProtoMessage()  {}

// ListTasksResponse mirrors fleet.proxy.v1.ListTasksResponse.
type ListTasksResponse struct {
	Tasks      []*TaskMsg `protobuf:"bytes,1,rep,name=tasks" json:"tasks,omitempty"`
	TotalCount int32      `protobuf:"varint,2,opt,name=total_count,json=totalCount" json:"total_count,omitempty"`
}

func (m *ListTasksResponse) Reset()         { *m = ListTasksResponse{} }
func (m *ListTasksResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *ListTasksResponse) ProtoMessage()  {}

// TaskMsg mirrors fleet.proxy.v1.Task.
type TaskMsg struct {
	TaskID         string `protobuf:"bytes,1,opt,name=task_id,json=taskId" json:"task_id,omitempty"`
	StoryID        string `protobuf:"bytes,2,opt,name=story_id,json=storyId" json:"story_id,omitempty"`
	Title          string `protobuf:"bytes,3,opt,name=title" json:"title,omitempty"`
	Description    string `protobuf:"bytes,4,opt,name=description" json:"description,omitempty"`
	Type           string `protobuf:"bytes,5,opt,name=type" json:"type,omitempty"`
	Status         string `protobuf:"bytes,6,opt,name=status" json:"status,omitempty"`
	AssignedTo     string `protobuf:"bytes,7,opt,name=assigned_to,json=assignedTo" json:"assigned_to,omitempty"`
	EstimatedHours int32  `protobuf:"varint,8,opt,name=estimated_hours,json=estimatedHours" json:"estimated_hours,omitempty"`
	Priority       int32  `protobuf:"varint,9,opt,name=priority" json:"priority,omitempty"`
	CreatedAt      string `protobuf:"bytes,10,opt,name=created_at,json=createdAt" json:"created_at,omitempty"`
	UpdatedAt      string `protobuf:"bytes,11,opt,name=updated_at,json=updatedAt" json:"updated_at,omitempty"`
}

func (m *TaskMsg) Reset()         { *m = TaskMsg{} }
func (m *TaskMsg) String() string { return fmt.Sprintf("%+v", *m) }
func (m *TaskMsg) ProtoMessage()  {}

// GetCeremonyInstanceRequest mirrors fleet.proxy.v1.GetCeremonyInstanceRequest.
type GetCeremonyInstanceRequest struct {
	InstanceID string `protobuf:"bytes,1,opt,name=instance_id,json=instanceId" json:"instance_id,omitempty"`
}

func (m *GetCeremonyInstanceRequest) Reset()         { *m = GetCeremonyInstanceRequest{} }
func (m *GetCeremonyInstanceRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *GetCeremonyInstanceRequest) ProtoMessage()  {}

// CeremonyInstanceResponse mirrors fleet.proxy.v1.CeremonyInstanceResponse.
type CeremonyInstanceResponse struct {
	Ceremony *CeremonyInstanceMsg `protobuf:"bytes,1,opt,name=ceremony" json:"ceremony,omitempty"`
}

func (m *CeremonyInstanceResponse) Reset()         { *m = CeremonyInstanceResponse{} }
func (m *CeremonyInstanceResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *CeremonyInstanceResponse) ProtoMessage()  {}

// ListCeremonyInstancesRequest mirrors fleet.proxy.v1.ListCeremonyInstancesRequest.
type ListCeremonyInstancesRequest struct {
	StateFilter      string `protobuf:"bytes,1,opt,name=state_filter,json=stateFilter" json:"state_filter,omitempty"`
	DefinitionFilter string `protobuf:"bytes,2,opt,name=definition_filter,json=definitionFilter" json:"definition_filter,omitempty"`
	StoryID          string `protobuf:"bytes,3,opt,name=story_id,json=storyId" json:"story_id,omitempty"`
	Limit            int32  `protobuf:"varint,4,opt,name=limit" json:"limit,omitempty"`
	Offset           int32  `protobuf:"varint,5,opt,name=offset" json:"offset,omitempty"`
}

func (m *ListCeremonyInstancesRequest) Reset()         { *m = ListCeremonyInstancesRequest{} }
func (m *ListCeremonyInstancesRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *ListCeremonyInstancesRequest) ProtoMessage()  {}

// ListCeremonyInstancesResponse mirrors fleet.proxy.v1.ListCeremonyInstancesResponse.
type ListCeremonyInstancesResponse struct {
	Ceremonies []*CeremonyInstanceMsg `protobuf:"bytes,1,rep,name=ceremonies" json:"ceremonies,omitempty"`
	TotalCount int32                  `protobuf:"varint,2,opt,name=total_count,json=totalCount" json:"total_count,omitempty"`
}

func (m *ListCeremonyInstancesResponse) Reset()         { *m = ListCeremonyInstancesResponse{} }
func (m *ListCeremonyInstancesResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *ListCeremonyInstancesResponse) ProtoMessage()  {}

// CeremonyInstanceMsg mirrors fleet.proxy.v1.CeremonyInstance.
type CeremonyInstanceMsg struct {
	InstanceID     string            `protobuf:"bytes,1,opt,name=instance_id,json=instanceId" json:"instance_id,omitempty"`
	CeremonyID     string            `protobuf:"bytes,2,opt,name=ceremony_id,json=ceremonyId" json:"ceremony_id,omitempty"`
	StoryID        string            `protobuf:"bytes,3,opt,name=story_id,json=storyId" json:"story_id,omitempty"`
	DefinitionName string            `protobuf:"bytes,4,opt,name=definition_name,json=definitionName" json:"definition_name,omitempty"`
	CurrentState   string            `protobuf:"bytes,5,opt,name=current_state,json=currentState" json:"current_state,omitempty"`
	Status         string            `protobuf:"bytes,6,opt,name=status" json:"status,omitempty"`
	CorrelationID  string            `protobuf:"bytes,7,opt,name=correlation_id,json=correlationId" json:"correlation_id,omitempty"`
	StepStatus     map[string]string `protobuf:"bytes,8,rep,name=step_status,json=stepStatus" json:"step_status,omitempty" protobuf_key:"bytes,1,opt" protobuf_val:"bytes,2,opt"`
	StepOutputs    map[string]string `protobuf:"bytes,9,rep,name=step_outputs,json=stepOutputs" json:"step_outputs,omitempty" protobuf_key:"bytes,1,opt" protobuf_val:"bytes,2,opt"`
	CreatedAt      string            `protobuf:"bytes,10,opt,name=created_at,json=createdAt" json:"created_at,omitempty"`
	UpdatedAt      string            `protobuf:"bytes,11,opt,name=updated_at,json=updatedAt" json:"updated_at,omitempty"`
}

func (m *CeremonyInstanceMsg) Reset()         { *m = CeremonyInstanceMsg{} }
func (m *CeremonyInstanceMsg) String() string { return fmt.Sprintf("%+v", *m) }
func (m *CeremonyInstanceMsg) ProtoMessage()  {}

// WatchEventsRequest mirrors fleet.proxy.v1.WatchEventsRequest.
type WatchEventsRequest struct {
	EventTypes []string `protobuf:"bytes,1,rep,name=event_types,json=eventTypes" json:"event_types,omitempty"`
	ProjectID  string   `protobuf:"bytes,2,opt,name=project_id,json=projectId" json:"project_id,omitempty"`
	Since      string   `protobuf:"bytes,3,opt,name=since" json:"since,omitempty"`
}

func (m *WatchEventsRequest) Reset()         { *m = WatchEventsRequest{} }
func (m *WatchEventsRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *WatchEventsRequest) ProtoMessage()  {}

// FleetEventMsg mirrors fleet.proxy.v1.FleetEvent.
type FleetEventMsg struct {
	EventType      string `protobuf:"bytes,1,opt,name=event_type,json=eventType" json:"event_type,omitempty"`
	IdempotencyKey string `protobuf:"bytes,2,opt,name=idempotency_key,json=idempotencyKey" json:"idempotency_key,omitempty"`
	CorrelationID  string `protobuf:"bytes,3,opt,name=correlation_id,json=correlationId" json:"correlation_id,omitempty"`
	Timestamp      string `protobuf:"bytes,4,opt,name=timestamp" json:"timestamp,omitempty"`
	Producer       string `protobuf:"bytes,5,opt,name=producer" json:"producer,omitempty"`
	Payload        []byte `protobuf:"bytes,6,opt,name=payload" json:"payload,omitempty"`
}

func (m *FleetEventMsg) Reset()         { *m = FleetEventMsg{} }
func (m *FleetEventMsg) String() string { return fmt.Sprintf("%+v", *m) }
func (m *FleetEventMsg) ProtoMessage()  {}

// ---------------------------------------------------------------------------
// FleetQueryService implementation
// ---------------------------------------------------------------------------

// FleetQueryService handles read-side gRPC RPCs by delegating to the
// application-layer query handlers.
type FleetQueryService struct {
	listProjects   *query.ListProjectsHandler
	listEpics      *query.ListEpicsHandler
	listStories    *query.ListStoriesHandler
	listTasks      *query.ListTasksHandler
	getCeremony    *query.GetCeremonyHandler
	listCeremonies *query.ListCeremoniesHandler
	watchEvents    *query.WatchEventsHandler
}

// NewFleetQueryService creates a FleetQueryService wired to all query handlers.
func NewFleetQueryService(
	listProjects *query.ListProjectsHandler,
	listEpics *query.ListEpicsHandler,
	listStories *query.ListStoriesHandler,
	listTasks *query.ListTasksHandler,
	getCeremony *query.GetCeremonyHandler,
	listCeremonies *query.ListCeremoniesHandler,
	watchEvents *query.WatchEventsHandler,
) *FleetQueryService {
	return &FleetQueryService{
		listProjects:   listProjects,
		listEpics:      listEpics,
		listStories:    listStories,
		listTasks:      listTasks,
		getCeremony:    getCeremony,
		listCeremonies: listCeremonies,
		watchEvents:    watchEvents,
	}
}

// HandleListProjects handles the ListProjects RPC.
func (s *FleetQueryService) HandleListProjects(ctx context.Context, req *ListProjectsRequest) (*ListProjectsResponse, error) {
	result, err := s.listProjects.Handle(ctx, query.ListProjectsQuery{
		StatusFilter: req.StatusFilter,
		Limit:        req.Limit,
		Offset:       req.Offset,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "list projects: %v", err)
	}

	projects := make([]*ProjectMsg, len(result.Projects))
	for i, p := range result.Projects {
		projects[i] = projectResultToMsg(p)
	}

	return &ListProjectsResponse{
		Projects:   projects,
		TotalCount: result.TotalCount,
	}, nil
}

// HandleListEpics handles the ListEpics RPC.
func (s *FleetQueryService) HandleListEpics(ctx context.Context, req *ListEpicsRequest) (*ListEpicsResponse, error) {
	result, err := s.listEpics.Handle(ctx, query.ListEpicsQuery{
		ProjectID:    req.ProjectID,
		StatusFilter: req.StatusFilter,
		Limit:        req.Limit,
		Offset:       req.Offset,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "list epics: %v", err)
	}

	epics := make([]*EpicMsg, len(result.Epics))
	for i, e := range result.Epics {
		epics[i] = epicResultToMsg(e)
	}

	return &ListEpicsResponse{
		Epics:      epics,
		TotalCount: result.TotalCount,
	}, nil
}

// HandleListStories handles the ListStories RPC.
func (s *FleetQueryService) HandleListStories(ctx context.Context, req *ListStoriesRequest) (*ListStoriesResponse, error) {
	result, err := s.listStories.Handle(ctx, query.ListStoriesQuery{
		EpicID:      req.EpicID,
		StateFilter: req.StateFilter,
		Limit:       req.Limit,
		Offset:      req.Offset,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "list stories: %v", err)
	}

	stories := make([]*StoryMsg, len(result.Stories))
	for i, st := range result.Stories {
		stories[i] = storyResultToMsg(st)
	}

	return &ListStoriesResponse{
		Stories:    stories,
		TotalCount: result.TotalCount,
	}, nil
}

// HandleListTasks handles the ListTasks RPC.
func (s *FleetQueryService) HandleListTasks(ctx context.Context, req *ListTasksRequest) (*ListTasksResponse, error) {
	result, err := s.listTasks.Handle(ctx, query.ListTasksQuery{
		StoryID:      req.StoryID,
		StatusFilter: req.StatusFilter,
		Limit:        req.Limit,
		Offset:       req.Offset,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "list tasks: %v", err)
	}

	tasks := make([]*TaskMsg, len(result.Tasks))
	for i, t := range result.Tasks {
		tasks[i] = taskResultToMsg(t)
	}

	return &ListTasksResponse{
		Tasks:      tasks,
		TotalCount: result.TotalCount,
	}, nil
}

// HandleGetCeremonyInstance handles the GetCeremonyInstance RPC.
func (s *FleetQueryService) HandleGetCeremonyInstance(ctx context.Context, req *GetCeremonyInstanceRequest) (*CeremonyInstanceResponse, error) {
	result, err := s.getCeremony.Handle(ctx, query.GetCeremonyQuery{
		InstanceID: req.InstanceID,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "get ceremony instance: %v", err)
	}

	return &CeremonyInstanceResponse{
		Ceremony: ceremonyResultToMsg(result),
	}, nil
}

// HandleListCeremonyInstances handles the ListCeremonyInstances RPC.
func (s *FleetQueryService) HandleListCeremonyInstances(ctx context.Context, req *ListCeremonyInstancesRequest) (*ListCeremonyInstancesResponse, error) {
	// The ListCeremoniesQuery uses ceremonyID + statusFilter. The proto request
	// uses stateFilter + definitionFilter. We map stateFilter -> statusFilter
	// and use storyID as the ceremonyID scope.
	result, err := s.listCeremonies.Handle(ctx, query.ListCeremoniesQuery{
		CeremonyID:   req.StoryID,
		StatusFilter: req.StateFilter,
		Limit:        req.Limit,
		Offset:       req.Offset,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "list ceremony instances: %v", err)
	}

	ceremonies := make([]*CeremonyInstanceMsg, len(result.Ceremonies))
	for i, c := range result.Ceremonies {
		ceremonies[i] = ceremonyResultToMsg(c)
	}

	return &ListCeremonyInstancesResponse{
		Ceremonies: ceremonies,
		TotalCount: result.TotalCount,
	}, nil
}

// HandleWatchEvents handles the WatchEvents server-streaming RPC. It opens
// an event subscription and streams events until the client disconnects or
// the context is cancelled.
func (s *FleetQueryService) HandleWatchEvents(req *WatchEventsRequest, stream grpc.ServerStream) error {
	ctx := stream.Context()

	// Build the event filter from the request.
	var types []event.EventType
	for _, t := range req.EventTypes {
		parsed, err := event.ParseEventType(t)
		if err != nil {
			return status.Errorf(codes.InvalidArgument, "invalid event type %q: %v", t, err)
		}
		types = append(types, parsed)
	}

	var projectID *string
	if req.ProjectID != "" {
		projectID = &req.ProjectID
	}

	filter, err := event.NewEventFilter(types, projectID)
	if err != nil {
		return status.Errorf(codes.InvalidArgument, "invalid event filter: %v", err)
	}

	eventCh, err := s.watchEvents.Handle(ctx, query.WatchEventsQuery{
		Filter: filter,
	})
	if err != nil {
		return status.Errorf(codes.Internal, "subscribe to events: %v", err)
	}

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case evt, ok := <-eventCh:
			if !ok {
				return nil
			}
			msg := &FleetEventMsg{
				EventType:      string(evt.Type),
				IdempotencyKey: evt.IdempotencyKey,
				CorrelationID:  evt.CorrelationID,
				Timestamp:      evt.Timestamp.Format("2006-01-02T15:04:05Z07:00"),
				Producer:       evt.Producer,
				Payload:        evt.Payload,
			}
			if err := stream.SendMsg(msg); err != nil {
				slog.Error("failed to send event to stream", "error", err)
				return err
			}
		}
	}
}

// ---------------------------------------------------------------------------
// Mapping helpers: ports result types -> gRPC message types
// ---------------------------------------------------------------------------

func projectResultToMsg(p ports.ProjectResult) *ProjectMsg {
	return &ProjectMsg{
		ProjectID:   p.ProjectID,
		Name:        p.Name,
		Description: p.Description,
		Status:      p.Status,
		Owner:       p.Owner,
		CreatedAt:   p.CreatedAt,
		UpdatedAt:   p.UpdatedAt,
	}
}

func epicResultToMsg(e ports.EpicResult) *EpicMsg {
	return &EpicMsg{
		EpicID:      e.EpicID,
		ProjectID:   e.ProjectID,
		Title:       e.Title,
		Description: e.Description,
		Status:      e.Status,
		CreatedAt:   e.CreatedAt,
		UpdatedAt:   e.UpdatedAt,
	}
}

func storyResultToMsg(s ports.StoryResult) *StoryMsg {
	return &StoryMsg{
		StoryID:   s.StoryID,
		EpicID:    s.EpicID,
		Title:     s.Title,
		Brief:     s.Brief,
		State:     s.State,
		CreatedAt: s.CreatedAt,
		UpdatedAt: s.UpdatedAt,
	}
}

func taskResultToMsg(t ports.TaskResult) *TaskMsg {
	return &TaskMsg{
		TaskID:         t.TaskID,
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
	}
}

func ceremonyResultToMsg(c ports.CeremonyResult) *CeremonyInstanceMsg {
	return &CeremonyInstanceMsg{
		InstanceID:     c.InstanceID,
		CeremonyID:     c.CeremonyID,
		StoryID:        c.StoryID,
		DefinitionName: c.DefinitionName,
		Status:         c.Status,
		StepStatus:     c.StepStatuses,
		CreatedAt:      c.CreatedAt,
		UpdatedAt:      c.UpdatedAt,
	}
}

// ---------------------------------------------------------------------------
// gRPC service registration
// ---------------------------------------------------------------------------

// RegisterFleetQueryService registers the FleetQueryService with the gRPC
// server using a manually constructed ServiceDesc.
func RegisterFleetQueryService(gs *grpc.Server, svc *FleetQueryService) {
	gs.RegisterService(&fleetQueryServiceDesc, svc)
}

// fleetQueryServer is the interface required by gRPC's ServiceDesc.HandlerType.
type fleetQueryServer interface{}

// fleetQueryServiceDesc is the grpc.ServiceDesc for the FleetQueryService.
var fleetQueryServiceDesc = grpc.ServiceDesc{
	ServiceName: "fleet.proxy.v1.FleetQueryService",
	HandlerType: (*fleetQueryServer)(nil),
	Methods: []grpc.MethodDesc{
		{MethodName: "ListProjects", Handler: qryListProjectsHandler},
		{MethodName: "ListEpics", Handler: qryListEpicsHandler},
		{MethodName: "ListStories", Handler: qryListStoriesHandler},
		{MethodName: "ListTasks", Handler: qryListTasksHandler},
		{MethodName: "GetCeremonyInstance", Handler: qryGetCeremonyInstanceHandler},
		{MethodName: "ListCeremonyInstances", Handler: qryListCeremonyInstancesHandler},
	},
	Streams: []grpc.StreamDesc{
		{
			StreamName:    "WatchEvents",
			Handler:       qryWatchEventsHandler,
			ServerStreams:  true,
			ClientStreams:  false,
		},
	},
	Metadata: "fleet/proxy/v1/fleet_proxy.proto",
}

// ---------------------------------------------------------------------------
// gRPC adapter functions
// ---------------------------------------------------------------------------

func qryListProjectsHandler(srv any, ctx context.Context, dec func(any) error, interceptor grpc.UnaryServerInterceptor) (any, error) {
	req := new(ListProjectsRequest)
	if err := dec(req); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(*FleetQueryService).HandleListProjects(ctx, req)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/fleet.proxy.v1.FleetQueryService/ListProjects"}
	return interceptor(ctx, req, info, func(ctx context.Context, r any) (any, error) {
		return srv.(*FleetQueryService).HandleListProjects(ctx, r.(*ListProjectsRequest))
	})
}

func qryListEpicsHandler(srv any, ctx context.Context, dec func(any) error, interceptor grpc.UnaryServerInterceptor) (any, error) {
	req := new(ListEpicsRequest)
	if err := dec(req); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(*FleetQueryService).HandleListEpics(ctx, req)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/fleet.proxy.v1.FleetQueryService/ListEpics"}
	return interceptor(ctx, req, info, func(ctx context.Context, r any) (any, error) {
		return srv.(*FleetQueryService).HandleListEpics(ctx, r.(*ListEpicsRequest))
	})
}

func qryListStoriesHandler(srv any, ctx context.Context, dec func(any) error, interceptor grpc.UnaryServerInterceptor) (any, error) {
	req := new(ListStoriesRequest)
	if err := dec(req); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(*FleetQueryService).HandleListStories(ctx, req)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/fleet.proxy.v1.FleetQueryService/ListStories"}
	return interceptor(ctx, req, info, func(ctx context.Context, r any) (any, error) {
		return srv.(*FleetQueryService).HandleListStories(ctx, r.(*ListStoriesRequest))
	})
}

func qryListTasksHandler(srv any, ctx context.Context, dec func(any) error, interceptor grpc.UnaryServerInterceptor) (any, error) {
	req := new(ListTasksRequest)
	if err := dec(req); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(*FleetQueryService).HandleListTasks(ctx, req)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/fleet.proxy.v1.FleetQueryService/ListTasks"}
	return interceptor(ctx, req, info, func(ctx context.Context, r any) (any, error) {
		return srv.(*FleetQueryService).HandleListTasks(ctx, r.(*ListTasksRequest))
	})
}

func qryGetCeremonyInstanceHandler(srv any, ctx context.Context, dec func(any) error, interceptor grpc.UnaryServerInterceptor) (any, error) {
	req := new(GetCeremonyInstanceRequest)
	if err := dec(req); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(*FleetQueryService).HandleGetCeremonyInstance(ctx, req)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/fleet.proxy.v1.FleetQueryService/GetCeremonyInstance"}
	return interceptor(ctx, req, info, func(ctx context.Context, r any) (any, error) {
		return srv.(*FleetQueryService).HandleGetCeremonyInstance(ctx, r.(*GetCeremonyInstanceRequest))
	})
}

func qryListCeremonyInstancesHandler(srv any, ctx context.Context, dec func(any) error, interceptor grpc.UnaryServerInterceptor) (any, error) {
	req := new(ListCeremonyInstancesRequest)
	if err := dec(req); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(*FleetQueryService).HandleListCeremonyInstances(ctx, req)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/fleet.proxy.v1.FleetQueryService/ListCeremonyInstances"}
	return interceptor(ctx, req, info, func(ctx context.Context, r any) (any, error) {
		return srv.(*FleetQueryService).HandleListCeremonyInstances(ctx, r.(*ListCeremonyInstancesRequest))
	})
}

func qryWatchEventsHandler(srv any, stream grpc.ServerStream) error {
	req := new(WatchEventsRequest)
	if err := stream.RecvMsg(req); err != nil {
		return err
	}
	return srv.(*FleetQueryService).HandleWatchEvents(req, stream)
}
