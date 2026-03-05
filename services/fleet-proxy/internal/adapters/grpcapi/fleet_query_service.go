package grpcapi

import (
	"context"
	"log/slog"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	proxyv1 "github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/gen/proxyv1"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/query"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/event"
)

// FleetQueryService handles read-side gRPC RPCs.
type FleetQueryService struct {
	proxyv1.UnimplementedFleetQueryServiceServer

	listProjects       *query.ListProjectsHandler
	listEpics          *query.ListEpicsHandler
	listStories        *query.ListStoriesHandler
	listTasks          *query.ListTasksHandler
	getCeremony        *query.GetCeremonyHandler
	listCeremonies     *query.ListCeremoniesHandler
	watchEvents        *query.WatchEventsHandler
	getBacklogReview   *query.GetBacklogReviewHandler
	listBacklogReviews *query.ListBacklogReviewsHandler
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
	getBacklogReview *query.GetBacklogReviewHandler,
	listBacklogReviews *query.ListBacklogReviewsHandler,
) *FleetQueryService {
	return &FleetQueryService{
		listProjects:       listProjects,
		listEpics:          listEpics,
		listStories:        listStories,
		listTasks:          listTasks,
		getCeremony:        getCeremony,
		listCeremonies:     listCeremonies,
		watchEvents:        watchEvents,
		getBacklogReview:   getBacklogReview,
		listBacklogReviews: listBacklogReviews,
	}
}

func (s *FleetQueryService) ListProjects(ctx context.Context, req *proxyv1.ListProjectsRequest) (*proxyv1.ListProjectsResponse, error) {
	result, err := s.listProjects.Handle(ctx, query.ListProjectsQuery{
		StatusFilter: req.GetStatusFilter(),
		Limit:        req.GetLimit(),
		Offset:       req.GetOffset(),
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "list projects: %v", err)
	}
	projects := make([]*proxyv1.Project, len(result.Projects))
	for i, p := range result.Projects {
		projects[i] = projectResultToProto(p)
	}
	return &proxyv1.ListProjectsResponse{Projects: projects, TotalCount: result.TotalCount}, nil
}

func (s *FleetQueryService) ListEpics(ctx context.Context, req *proxyv1.ListEpicsRequest) (*proxyv1.ListEpicsResponse, error) {
	result, err := s.listEpics.Handle(ctx, query.ListEpicsQuery{
		ProjectID:    req.GetProjectId(),
		StatusFilter: req.GetStatusFilter(),
		Limit:        req.GetLimit(),
		Offset:       req.GetOffset(),
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "list epics: %v", err)
	}
	epics := make([]*proxyv1.Epic, len(result.Epics))
	for i, e := range result.Epics {
		epics[i] = epicResultToProto(e)
	}
	return &proxyv1.ListEpicsResponse{Epics: epics, TotalCount: result.TotalCount}, nil
}

func (s *FleetQueryService) ListStories(ctx context.Context, req *proxyv1.ListStoriesRequest) (*proxyv1.ListStoriesResponse, error) {
	result, err := s.listStories.Handle(ctx, query.ListStoriesQuery{
		EpicID:      req.GetEpicId(),
		StateFilter: req.GetStateFilter(),
		Limit:       req.GetLimit(),
		Offset:      req.GetOffset(),
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "list stories: %v", err)
	}
	stories := make([]*proxyv1.Story, len(result.Stories))
	for i, st := range result.Stories {
		stories[i] = storyResultToProto(st)
	}
	return &proxyv1.ListStoriesResponse{Stories: stories, TotalCount: result.TotalCount}, nil
}

func (s *FleetQueryService) ListTasks(ctx context.Context, req *proxyv1.ListTasksRequest) (*proxyv1.ListTasksResponse, error) {
	result, err := s.listTasks.Handle(ctx, query.ListTasksQuery{
		StoryID:      req.GetStoryId(),
		StatusFilter: req.GetStatusFilter(),
		Limit:        req.GetLimit(),
		Offset:       req.GetOffset(),
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "list tasks: %v", err)
	}
	tasks := make([]*proxyv1.Task, len(result.Tasks))
	for i, t := range result.Tasks {
		tasks[i] = taskResultToProto(t)
	}
	return &proxyv1.ListTasksResponse{Tasks: tasks, TotalCount: result.TotalCount}, nil
}

func (s *FleetQueryService) GetCeremonyInstance(ctx context.Context, req *proxyv1.GetCeremonyInstanceRequest) (*proxyv1.CeremonyInstanceResponse, error) {
	result, err := s.getCeremony.Handle(ctx, query.GetCeremonyQuery{
		InstanceID: req.GetInstanceId(),
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "get ceremony instance: %v", err)
	}
	return &proxyv1.CeremonyInstanceResponse{Ceremony: ceremonyResultToProto(result)}, nil
}

func (s *FleetQueryService) ListCeremonyInstances(ctx context.Context, req *proxyv1.ListCeremonyInstancesRequest) (*proxyv1.ListCeremonyInstancesResponse, error) {
	result, err := s.listCeremonies.Handle(ctx, query.ListCeremoniesQuery{
		CeremonyID:   req.GetStoryId(),
		StatusFilter: req.GetStateFilter(),
		Limit:        req.GetLimit(),
		Offset:       req.GetOffset(),
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "list ceremony instances: %v", err)
	}
	ceremonies := make([]*proxyv1.CeremonyInstance, len(result.Ceremonies))
	for i, c := range result.Ceremonies {
		ceremonies[i] = ceremonyResultToProto(c)
	}
	return &proxyv1.ListCeremonyInstancesResponse{Ceremonies: ceremonies, TotalCount: result.TotalCount}, nil
}

func (s *FleetQueryService) WatchEvents(req *proxyv1.WatchEventsRequest, stream grpc.ServerStreamingServer[proxyv1.FleetEvent]) error {
	ctx := stream.Context()
	slog.Info("WatchEvents: stream opened", "event_types", req.GetEventTypes(), "project_id", req.GetProjectId())

	var types []event.EventType
	for _, t := range req.GetEventTypes() {
		parsed, err := event.ParseEventType(t)
		if err != nil {
			return status.Errorf(codes.InvalidArgument, "invalid event type %q: %v", t, err)
		}
		types = append(types, parsed)
	}

	var projectID *string
	if req.GetProjectId() != "" {
		pid := req.GetProjectId()
		projectID = &pid
	}

	var filter event.EventFilter
	if len(types) > 0 || projectID != nil {
		var filterErr error
		filter, filterErr = event.NewEventFilter(types, projectID)
		if filterErr != nil {
			return status.Errorf(codes.InvalidArgument, "invalid event filter: %v", filterErr)
		}
	}

	slog.Info("WatchEvents: subscribing to events", "types", len(types), "has_project", projectID != nil)
	eventCh, err := s.watchEvents.Handle(ctx, query.WatchEventsQuery{Filter: filter})
	if err != nil {
		slog.Error("WatchEvents: subscribe failed", "error", err)
		return status.Errorf(codes.Internal, "subscribe to events: %v", err)
	}

	slog.Info("WatchEvents: subscription active, waiting for events")
	for {
		select {
		case <-ctx.Done():
			slog.Info("WatchEvents: client disconnected", "error", ctx.Err())
			return status.FromContextError(ctx.Err()).Err()
		case evt, ok := <-eventCh:
			if !ok {
				slog.Warn("WatchEvents: event channel closed unexpectedly")
				return nil
			}
			msg := &proxyv1.FleetEvent{
				EventType:      string(evt.Type),
				IdempotencyKey: evt.IdempotencyKey,
				CorrelationId:  evt.CorrelationID,
				Timestamp:      evt.Timestamp.Format("2006-01-02T15:04:05Z07:00"),
				Producer:       evt.Producer,
				Payload:        evt.Payload,
			}
			if err := stream.Send(msg); err != nil {
				slog.Error("failed to send event to stream", "error", err)
				return err
			}
		}
	}
}

func (s *FleetQueryService) GetBacklogReview(ctx context.Context, req *proxyv1.GetBacklogReviewRequest) (*proxyv1.GetBacklogReviewResponse, error) {
	result, err := s.getBacklogReview.Handle(ctx, query.GetBacklogReviewQuery{
		CeremonyID: req.GetCeremonyId(),
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "get backlog review: %v", err)
	}
	return &proxyv1.GetBacklogReviewResponse{
		Ceremony: backlogReviewResultToProto(result),
		Success:  true,
		Message:  "backlog review retrieved",
	}, nil
}

func (s *FleetQueryService) ListBacklogReviews(ctx context.Context, req *proxyv1.ListBacklogReviewsRequest) (*proxyv1.ListBacklogReviewsResponse, error) {
	result, err := s.listBacklogReviews.Handle(ctx, query.ListBacklogReviewsQuery{
		StatusFilter: req.GetStatusFilter(),
		Limit:        req.GetLimit(),
		Offset:       req.GetOffset(),
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "list backlog reviews: %v", err)
	}
	ceremonies := make([]*proxyv1.BacklogReview, len(result.Reviews))
	for i, r := range result.Reviews {
		ceremonies[i] = backlogReviewResultToProto(r)
	}
	return &proxyv1.ListBacklogReviewsResponse{Ceremonies: ceremonies, TotalCount: result.TotalCount}, nil
}

// ---------------------------------------------------------------------------
// Mapping helpers: ports result types -> generated proto types
// ---------------------------------------------------------------------------

func projectResultToProto(p ports.ProjectResult) *proxyv1.Project {
	return &proxyv1.Project{
		ProjectId:   p.ProjectID,
		Name:        p.Name,
		Description: p.Description,
		Status:      p.Status,
		Owner:       p.Owner,
		CreatedAt:   p.CreatedAt,
		UpdatedAt:   p.UpdatedAt,
	}
}

func epicResultToProto(e ports.EpicResult) *proxyv1.Epic {
	return &proxyv1.Epic{
		EpicId:      e.EpicID,
		ProjectId:   e.ProjectID,
		Title:       e.Title,
		Description: e.Description,
		Status:      e.Status,
		CreatedAt:   e.CreatedAt,
		UpdatedAt:   e.UpdatedAt,
	}
}

func storyResultToProto(s ports.StoryResult) *proxyv1.Story {
	return &proxyv1.Story{
		StoryId:   s.StoryID,
		EpicId:    s.EpicID,
		Title:     s.Title,
		Brief:     s.Brief,
		State:     s.State,
		DorScore:  s.DorScore,
		CreatedBy: s.CreatedBy,
		CreatedAt: s.CreatedAt,
		UpdatedAt: s.UpdatedAt,
	}
}

func taskResultToProto(t ports.TaskResult) *proxyv1.Task {
	return &proxyv1.Task{
		TaskId:         t.TaskID,
		StoryId:        t.StoryID,
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

func ceremonyResultToProto(c ports.CeremonyResult) *proxyv1.CeremonyInstance {
	return &proxyv1.CeremonyInstance{
		InstanceId:     c.InstanceID,
		CeremonyId:     c.CeremonyID,
		StoryId:        c.StoryID,
		DefinitionName: c.DefinitionName,
		CurrentState:   c.CurrentState,
		Status:         c.Status,
		CorrelationId:  c.CorrelationID,
		StepStatus:     c.StepStatuses,
		StepOutputs:    c.StepOutputs,
		CreatedAt:      c.CreatedAt,
		UpdatedAt:      c.UpdatedAt,
	}
}
