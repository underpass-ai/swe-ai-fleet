package grpc

import "fmt"

// ---------------------------------------------------------------------------
// Hand-crafted proto message types for fleet.proxy.v1.FleetCommandService
// and fleet.proxy.v1.FleetQueryService. These match the wire format defined
// in specs/fleet/proxy/v1/fleet_proxy.proto.
// ---------------------------------------------------------------------------

// --- Command request/response types ---

type CreateProjectRequest struct {
	RequestID   string `protobuf:"bytes,1,opt,name=request_id,json=requestId" json:"request_id,omitempty"`
	Name        string `protobuf:"bytes,2,opt,name=name" json:"name,omitempty"`
	Description string `protobuf:"bytes,3,opt,name=description" json:"description,omitempty"`
}

func (m *CreateProjectRequest) Reset()         { *m = CreateProjectRequest{} }
func (m *CreateProjectRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *CreateProjectRequest) ProtoMessage()  {}

type CreateProjectResponse struct {
	ProjectID string `protobuf:"bytes,1,opt,name=project_id,json=projectId" json:"project_id,omitempty"`
	Success   bool   `protobuf:"varint,2,opt,name=success" json:"success,omitempty"`
	Message   string `protobuf:"bytes,3,opt,name=message" json:"message,omitempty"`
}

func (m *CreateProjectResponse) Reset()         { *m = CreateProjectResponse{} }
func (m *CreateProjectResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *CreateProjectResponse) ProtoMessage()  {}

type CreateStoryRequest struct {
	RequestID string `protobuf:"bytes,1,opt,name=request_id,json=requestId" json:"request_id,omitempty"`
	EpicID    string `protobuf:"bytes,2,opt,name=epic_id,json=epicId" json:"epic_id,omitempty"`
	Title     string `protobuf:"bytes,3,opt,name=title" json:"title,omitempty"`
	Brief     string `protobuf:"bytes,4,opt,name=brief" json:"brief,omitempty"`
}

func (m *CreateStoryRequest) Reset()         { *m = CreateStoryRequest{} }
func (m *CreateStoryRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *CreateStoryRequest) ProtoMessage()  {}

type CreateStoryResponse struct {
	StoryID string `protobuf:"bytes,1,opt,name=story_id,json=storyId" json:"story_id,omitempty"`
	Success bool   `protobuf:"varint,2,opt,name=success" json:"success,omitempty"`
	Message string `protobuf:"bytes,3,opt,name=message" json:"message,omitempty"`
}

func (m *CreateStoryResponse) Reset()         { *m = CreateStoryResponse{} }
func (m *CreateStoryResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *CreateStoryResponse) ProtoMessage()  {}

type TransitionStoryRequest struct {
	StoryID     string `protobuf:"bytes,1,opt,name=story_id,json=storyId" json:"story_id,omitempty"`
	TargetState string `protobuf:"bytes,2,opt,name=target_state,json=targetState" json:"target_state,omitempty"`
}

func (m *TransitionStoryRequest) Reset()         { *m = TransitionStoryRequest{} }
func (m *TransitionStoryRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *TransitionStoryRequest) ProtoMessage()  {}

type TransitionStoryResponse struct {
	Success bool   `protobuf:"varint,1,opt,name=success" json:"success,omitempty"`
	Message string `protobuf:"bytes,2,opt,name=message" json:"message,omitempty"`
}

func (m *TransitionStoryResponse) Reset()         { *m = TransitionStoryResponse{} }
func (m *TransitionStoryResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *TransitionStoryResponse) ProtoMessage()  {}

type StartPlanningCeremonyRequest struct {
	RequestID      string   `protobuf:"bytes,1,opt,name=request_id,json=requestId" json:"request_id,omitempty"`
	CeremonyID     string   `protobuf:"bytes,2,opt,name=ceremony_id,json=ceremonyId" json:"ceremony_id,omitempty"`
	DefinitionName string   `protobuf:"bytes,3,opt,name=definition_name,json=definitionName" json:"definition_name,omitempty"`
	StoryID        string   `protobuf:"bytes,4,opt,name=story_id,json=storyId" json:"story_id,omitempty"`
	StepIDs        []string `protobuf:"bytes,5,rep,name=step_ids,json=stepIds" json:"step_ids,omitempty"`
}

func (m *StartPlanningCeremonyRequest) Reset()         { *m = StartPlanningCeremonyRequest{} }
func (m *StartPlanningCeremonyRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *StartPlanningCeremonyRequest) ProtoMessage()  {}

type StartPlanningCeremonyResponse struct {
	InstanceID string `protobuf:"bytes,1,opt,name=instance_id,json=instanceId" json:"instance_id,omitempty"`
	Status     string `protobuf:"bytes,2,opt,name=status" json:"status,omitempty"`
	Message    string `protobuf:"bytes,3,opt,name=message" json:"message,omitempty"`
}

func (m *StartPlanningCeremonyResponse) Reset()         { *m = StartPlanningCeremonyResponse{} }
func (m *StartPlanningCeremonyResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *StartPlanningCeremonyResponse) ProtoMessage()  {}

type ApproveDecisionRequest struct {
	StoryID    string `protobuf:"bytes,1,opt,name=story_id,json=storyId" json:"story_id,omitempty"`
	DecisionID string `protobuf:"bytes,2,opt,name=decision_id,json=decisionId" json:"decision_id,omitempty"`
	Comment    string `protobuf:"bytes,3,opt,name=comment" json:"comment,omitempty"`
}

func (m *ApproveDecisionRequest) Reset()         { *m = ApproveDecisionRequest{} }
func (m *ApproveDecisionRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *ApproveDecisionRequest) ProtoMessage()  {}

type ApproveDecisionResponse struct {
	Success bool   `protobuf:"varint,1,opt,name=success" json:"success,omitempty"`
	Message string `protobuf:"bytes,2,opt,name=message" json:"message,omitempty"`
}

func (m *ApproveDecisionResponse) Reset()         { *m = ApproveDecisionResponse{} }
func (m *ApproveDecisionResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *ApproveDecisionResponse) ProtoMessage()  {}

type RejectDecisionRequest struct {
	StoryID    string `protobuf:"bytes,1,opt,name=story_id,json=storyId" json:"story_id,omitempty"`
	DecisionID string `protobuf:"bytes,2,opt,name=decision_id,json=decisionId" json:"decision_id,omitempty"`
	Reason     string `protobuf:"bytes,3,opt,name=reason" json:"reason,omitempty"`
}

func (m *RejectDecisionRequest) Reset()         { *m = RejectDecisionRequest{} }
func (m *RejectDecisionRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *RejectDecisionRequest) ProtoMessage()  {}

type RejectDecisionResponse struct {
	Success bool   `protobuf:"varint,1,opt,name=success" json:"success,omitempty"`
	Message string `protobuf:"bytes,2,opt,name=message" json:"message,omitempty"`
}

func (m *RejectDecisionResponse) Reset()         { *m = RejectDecisionResponse{} }
func (m *RejectDecisionResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *RejectDecisionResponse) ProtoMessage()  {}

// --- Query request/response types ---

type ListProjectsRequest struct {
	StatusFilter string `protobuf:"bytes,1,opt,name=status_filter,json=statusFilter" json:"status_filter,omitempty"`
	Limit        int32  `protobuf:"varint,2,opt,name=limit" json:"limit,omitempty"`
	Offset       int32  `protobuf:"varint,3,opt,name=offset" json:"offset,omitempty"`
}

func (m *ListProjectsRequest) Reset()         { *m = ListProjectsRequest{} }
func (m *ListProjectsRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *ListProjectsRequest) ProtoMessage()  {}

type ListProjectsResponse struct {
	Projects   []*ProjectMsg `protobuf:"bytes,1,rep,name=projects" json:"projects,omitempty"`
	TotalCount int32         `protobuf:"varint,2,opt,name=total_count,json=totalCount" json:"total_count,omitempty"`
}

func (m *ListProjectsResponse) Reset()         { *m = ListProjectsResponse{} }
func (m *ListProjectsResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *ListProjectsResponse) ProtoMessage()  {}

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

// --- Epic command/query types ---

type CreateEpicRequest struct {
	RequestID   string `protobuf:"bytes,1,opt,name=request_id,json=requestId" json:"request_id,omitempty"`
	ProjectID   string `protobuf:"bytes,2,opt,name=project_id,json=projectId" json:"project_id,omitempty"`
	Title       string `protobuf:"bytes,3,opt,name=title" json:"title,omitempty"`
	Description string `protobuf:"bytes,4,opt,name=description" json:"description,omitempty"`
}

func (m *CreateEpicRequest) Reset()         { *m = CreateEpicRequest{} }
func (m *CreateEpicRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *CreateEpicRequest) ProtoMessage()  {}

type CreateEpicResponse struct {
	EpicID  string `protobuf:"bytes,1,opt,name=epic_id,json=epicId" json:"epic_id,omitempty"`
	Success bool   `protobuf:"varint,2,opt,name=success" json:"success,omitempty"`
	Message string `protobuf:"bytes,3,opt,name=message" json:"message,omitempty"`
}

func (m *CreateEpicResponse) Reset()         { *m = CreateEpicResponse{} }
func (m *CreateEpicResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *CreateEpicResponse) ProtoMessage()  {}

type ListEpicsRequest struct {
	ProjectID    string `protobuf:"bytes,1,opt,name=project_id,json=projectId" json:"project_id,omitempty"`
	StatusFilter string `protobuf:"bytes,2,opt,name=status_filter,json=statusFilter" json:"status_filter,omitempty"`
	Limit        int32  `protobuf:"varint,3,opt,name=limit" json:"limit,omitempty"`
	Offset       int32  `protobuf:"varint,4,opt,name=offset" json:"offset,omitempty"`
}

func (m *ListEpicsRequest) Reset()         { *m = ListEpicsRequest{} }
func (m *ListEpicsRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *ListEpicsRequest) ProtoMessage()  {}

type ListEpicsResponse struct {
	Epics      []*EpicMsg `protobuf:"bytes,1,rep,name=epics" json:"epics,omitempty"`
	TotalCount int32      `protobuf:"varint,2,opt,name=total_count,json=totalCount" json:"total_count,omitempty"`
}

func (m *ListEpicsResponse) Reset()         { *m = ListEpicsResponse{} }
func (m *ListEpicsResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *ListEpicsResponse) ProtoMessage()  {}

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

// --- Event streaming types ---

// WatchEventsRequest mirrors fleet.proxy.v1.WatchEventsRequest.
type WatchEventsRequest struct {
	EventTypes []string `protobuf:"bytes,1,rep,name=event_types,json=eventTypes" json:"event_types,omitempty"`
	ProjectID  string   `protobuf:"bytes,2,opt,name=project_id,json=projectId" json:"project_id,omitempty"`
	Since      string   `protobuf:"bytes,3,opt,name=since" json:"since,omitempty"`
}

func (m *WatchEventsRequest) Reset()         { *m = WatchEventsRequest{} }
func (m *WatchEventsRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *WatchEventsRequest) ProtoMessage()  {}

// FleetEventMsg mirrors fleet.proxy.v1.FleetEvent (server-streamed response).
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

// --- Story query types ---

type ListStoriesRequest struct {
	EpicID      string `protobuf:"bytes,1,opt,name=epic_id,json=epicId" json:"epic_id,omitempty"`
	StateFilter string `protobuf:"bytes,2,opt,name=state_filter,json=stateFilter" json:"state_filter,omitempty"`
	Limit       int32  `protobuf:"varint,3,opt,name=limit" json:"limit,omitempty"`
	Offset      int32  `protobuf:"varint,4,opt,name=offset" json:"offset,omitempty"`
}

func (m *ListStoriesRequest) Reset()         { *m = ListStoriesRequest{} }
func (m *ListStoriesRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *ListStoriesRequest) ProtoMessage()  {}

type ListStoriesResponse struct {
	Stories    []*StoryMsg `protobuf:"bytes,1,rep,name=stories" json:"stories,omitempty"`
	TotalCount int32       `protobuf:"varint,2,opt,name=total_count,json=totalCount" json:"total_count,omitempty"`
}

func (m *ListStoriesResponse) Reset()         { *m = ListStoriesResponse{} }
func (m *ListStoriesResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *ListStoriesResponse) ProtoMessage()  {}

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

// --- Task command/query types ---

type CreateTaskRequest struct {
	RequestID      string `protobuf:"bytes,1,opt,name=request_id,json=requestId" json:"request_id,omitempty"`
	StoryID        string `protobuf:"bytes,2,opt,name=story_id,json=storyId" json:"story_id,omitempty"`
	Title          string `protobuf:"bytes,3,opt,name=title" json:"title,omitempty"`
	Description    string `protobuf:"bytes,4,opt,name=description" json:"description,omitempty"`
	Type           string `protobuf:"bytes,5,opt,name=type" json:"type,omitempty"`
	AssignedTo     string `protobuf:"bytes,6,opt,name=assigned_to,json=assignedTo" json:"assigned_to,omitempty"`
	EstimatedHours int32  `protobuf:"varint,7,opt,name=estimated_hours,json=estimatedHours" json:"estimated_hours,omitempty"`
	Priority       int32  `protobuf:"varint,8,opt,name=priority" json:"priority,omitempty"`
}

func (m *CreateTaskRequest) Reset()         { *m = CreateTaskRequest{} }
func (m *CreateTaskRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *CreateTaskRequest) ProtoMessage()  {}

type CreateTaskResponse struct {
	TaskID  string `protobuf:"bytes,1,opt,name=task_id,json=taskId" json:"task_id,omitempty"`
	Success bool   `protobuf:"varint,2,opt,name=success" json:"success,omitempty"`
	Message string `protobuf:"bytes,3,opt,name=message" json:"message,omitempty"`
}

func (m *CreateTaskResponse) Reset()         { *m = CreateTaskResponse{} }
func (m *CreateTaskResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *CreateTaskResponse) ProtoMessage()  {}

type ListTasksRequest struct {
	StoryID      string `protobuf:"bytes,1,opt,name=story_id,json=storyId" json:"story_id,omitempty"`
	StatusFilter string `protobuf:"bytes,2,opt,name=status_filter,json=statusFilter" json:"status_filter,omitempty"`
	Limit        int32  `protobuf:"varint,3,opt,name=limit" json:"limit,omitempty"`
	Offset       int32  `protobuf:"varint,4,opt,name=offset" json:"offset,omitempty"`
}

func (m *ListTasksRequest) Reset()         { *m = ListTasksRequest{} }
func (m *ListTasksRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *ListTasksRequest) ProtoMessage()  {}

type ListTasksResponse struct {
	Tasks      []*TaskMsg `protobuf:"bytes,1,rep,name=tasks" json:"tasks,omitempty"`
	TotalCount int32      `protobuf:"varint,2,opt,name=total_count,json=totalCount" json:"total_count,omitempty"`
}

func (m *ListTasksResponse) Reset()         { *m = ListTasksResponse{} }
func (m *ListTasksResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *ListTasksResponse) ProtoMessage()  {}

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

// --- Backlog review command types ---

type StartBacklogReviewRequest struct {
	RequestID  string `protobuf:"bytes,1,opt,name=request_id,json=requestId" json:"request_id,omitempty"`
	CeremonyID string `protobuf:"bytes,2,opt,name=ceremony_id,json=ceremonyId" json:"ceremony_id,omitempty"`
}

func (m *StartBacklogReviewRequest) Reset()         { *m = StartBacklogReviewRequest{} }
func (m *StartBacklogReviewRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *StartBacklogReviewRequest) ProtoMessage()  {}

type StartBacklogReviewResponse struct {
	Ceremony                    *BacklogReviewMsgWire `protobuf:"bytes,1,opt,name=ceremony" json:"ceremony,omitempty"`
	Success                     bool                  `protobuf:"varint,2,opt,name=success" json:"success,omitempty"`
	Message                     string                `protobuf:"bytes,3,opt,name=message" json:"message,omitempty"`
	TotalDeliberationsSubmitted int32                 `protobuf:"varint,4,opt,name=total_deliberations_submitted,json=totalDeliberationsSubmitted" json:"total_deliberations_submitted,omitempty"`
}

func (m *StartBacklogReviewResponse) Reset()         { *m = StartBacklogReviewResponse{} }
func (m *StartBacklogReviewResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *StartBacklogReviewResponse) ProtoMessage()  {}

type CreateBacklogReviewRequest struct {
	RequestID string   `protobuf:"bytes,1,opt,name=request_id,json=requestId" json:"request_id,omitempty"`
	StoryIDs  []string `protobuf:"bytes,2,rep,name=story_ids,json=storyIds" json:"story_ids,omitempty"`
}

func (m *CreateBacklogReviewRequest) Reset()         { *m = CreateBacklogReviewRequest{} }
func (m *CreateBacklogReviewRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *CreateBacklogReviewRequest) ProtoMessage()  {}

type CreateBacklogReviewResponse struct {
	Ceremony *BacklogReviewMsgWire `protobuf:"bytes,1,opt,name=ceremony" json:"ceremony,omitempty"`
	Success  bool                  `protobuf:"varint,2,opt,name=success" json:"success,omitempty"`
	Message  string                `protobuf:"bytes,3,opt,name=message" json:"message,omitempty"`
}

func (m *CreateBacklogReviewResponse) Reset()         { *m = CreateBacklogReviewResponse{} }
func (m *CreateBacklogReviewResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *CreateBacklogReviewResponse) ProtoMessage()  {}

type ApproveReviewPlanProxyRequest struct {
	CeremonyID         string `protobuf:"bytes,1,opt,name=ceremony_id,json=ceremonyId" json:"ceremony_id,omitempty"`
	StoryID            string `protobuf:"bytes,2,opt,name=story_id,json=storyId" json:"story_id,omitempty"`
	PONotes            string `protobuf:"bytes,3,opt,name=po_notes,json=poNotes" json:"po_notes,omitempty"`
	POConcerns         string `protobuf:"bytes,4,opt,name=po_concerns,json=poConcerns" json:"po_concerns,omitempty"`
	PriorityAdjustment string `protobuf:"bytes,5,opt,name=priority_adjustment,json=priorityAdjustment" json:"priority_adjustment,omitempty"`
	POPriorityReason   string `protobuf:"bytes,6,opt,name=po_priority_reason,json=poPriorityReason" json:"po_priority_reason,omitempty"`
}

func (m *ApproveReviewPlanProxyRequest) Reset()         { *m = ApproveReviewPlanProxyRequest{} }
func (m *ApproveReviewPlanProxyRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *ApproveReviewPlanProxyRequest) ProtoMessage()  {}

type ApproveReviewPlanProxyResponse struct {
	Ceremony *BacklogReviewMsgWire `protobuf:"bytes,1,opt,name=ceremony" json:"ceremony,omitempty"`
	PlanID   string                `protobuf:"bytes,2,opt,name=plan_id,json=planId" json:"plan_id,omitempty"`
	Success  bool                  `protobuf:"varint,3,opt,name=success" json:"success,omitempty"`
	Message  string                `protobuf:"bytes,4,opt,name=message" json:"message,omitempty"`
}

func (m *ApproveReviewPlanProxyResponse) Reset()         { *m = ApproveReviewPlanProxyResponse{} }
func (m *ApproveReviewPlanProxyResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *ApproveReviewPlanProxyResponse) ProtoMessage()  {}

type RejectReviewPlanProxyRequest struct {
	CeremonyID string `protobuf:"bytes,1,opt,name=ceremony_id,json=ceremonyId" json:"ceremony_id,omitempty"`
	StoryID    string `protobuf:"bytes,2,opt,name=story_id,json=storyId" json:"story_id,omitempty"`
	Reason     string `protobuf:"bytes,3,opt,name=reason" json:"reason,omitempty"`
}

func (m *RejectReviewPlanProxyRequest) Reset()         { *m = RejectReviewPlanProxyRequest{} }
func (m *RejectReviewPlanProxyRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *RejectReviewPlanProxyRequest) ProtoMessage()  {}

type RejectReviewPlanProxyResponse struct {
	Ceremony *BacklogReviewMsgWire `protobuf:"bytes,1,opt,name=ceremony" json:"ceremony,omitempty"`
	Success  bool                  `protobuf:"varint,2,opt,name=success" json:"success,omitempty"`
	Message  string                `protobuf:"bytes,3,opt,name=message" json:"message,omitempty"`
}

func (m *RejectReviewPlanProxyResponse) Reset()         { *m = RejectReviewPlanProxyResponse{} }
func (m *RejectReviewPlanProxyResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *RejectReviewPlanProxyResponse) ProtoMessage()  {}

type CompleteBacklogReviewRequest struct {
	CeremonyID string `protobuf:"bytes,1,opt,name=ceremony_id,json=ceremonyId" json:"ceremony_id,omitempty"`
}

func (m *CompleteBacklogReviewRequest) Reset()         { *m = CompleteBacklogReviewRequest{} }
func (m *CompleteBacklogReviewRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *CompleteBacklogReviewRequest) ProtoMessage()  {}

type CompleteBacklogReviewResponse struct {
	Ceremony *BacklogReviewMsgWire `protobuf:"bytes,1,opt,name=ceremony" json:"ceremony,omitempty"`
	Success  bool                  `protobuf:"varint,2,opt,name=success" json:"success,omitempty"`
	Message  string                `protobuf:"bytes,3,opt,name=message" json:"message,omitempty"`
}

func (m *CompleteBacklogReviewResponse) Reset()         { *m = CompleteBacklogReviewResponse{} }
func (m *CompleteBacklogReviewResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *CompleteBacklogReviewResponse) ProtoMessage()  {}

type CancelBacklogReviewRequest struct {
	CeremonyID string `protobuf:"bytes,1,opt,name=ceremony_id,json=ceremonyId" json:"ceremony_id,omitempty"`
}

func (m *CancelBacklogReviewRequest) Reset()         { *m = CancelBacklogReviewRequest{} }
func (m *CancelBacklogReviewRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *CancelBacklogReviewRequest) ProtoMessage()  {}

type CancelBacklogReviewResponse struct {
	Ceremony *BacklogReviewMsgWire `protobuf:"bytes,1,opt,name=ceremony" json:"ceremony,omitempty"`
	Success  bool                  `protobuf:"varint,2,opt,name=success" json:"success,omitempty"`
	Message  string                `protobuf:"bytes,3,opt,name=message" json:"message,omitempty"`
}

func (m *CancelBacklogReviewResponse) Reset()         { *m = CancelBacklogReviewResponse{} }
func (m *CancelBacklogReviewResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *CancelBacklogReviewResponse) ProtoMessage()  {}

// --- Backlog review query types ---

type GetBacklogReviewProxyRequest struct {
	CeremonyID string `protobuf:"bytes,1,opt,name=ceremony_id,json=ceremonyId" json:"ceremony_id,omitempty"`
}

func (m *GetBacklogReviewProxyRequest) Reset()         { *m = GetBacklogReviewProxyRequest{} }
func (m *GetBacklogReviewProxyRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *GetBacklogReviewProxyRequest) ProtoMessage()  {}

type GetBacklogReviewProxyResponse struct {
	Ceremony *BacklogReviewMsgWire `protobuf:"bytes,1,opt,name=ceremony" json:"ceremony,omitempty"`
	Success  bool                  `protobuf:"varint,2,opt,name=success" json:"success,omitempty"`
	Message  string                `protobuf:"bytes,3,opt,name=message" json:"message,omitempty"`
}

func (m *GetBacklogReviewProxyResponse) Reset()         { *m = GetBacklogReviewProxyResponse{} }
func (m *GetBacklogReviewProxyResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *GetBacklogReviewProxyResponse) ProtoMessage()  {}

type ListBacklogReviewsProxyRequest struct {
	StatusFilter string `protobuf:"bytes,1,opt,name=status_filter,json=statusFilter" json:"status_filter,omitempty"`
	Limit        int32  `protobuf:"varint,2,opt,name=limit" json:"limit,omitempty"`
	Offset       int32  `protobuf:"varint,3,opt,name=offset" json:"offset,omitempty"`
}

func (m *ListBacklogReviewsProxyRequest) Reset()         { *m = ListBacklogReviewsProxyRequest{} }
func (m *ListBacklogReviewsProxyRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *ListBacklogReviewsProxyRequest) ProtoMessage()  {}

type ListBacklogReviewsProxyResponse struct {
	Ceremonies []*BacklogReviewMsgWire `protobuf:"bytes,1,rep,name=ceremonies" json:"ceremonies,omitempty"`
	TotalCount int32                   `protobuf:"varint,2,opt,name=total_count,json=totalCount" json:"total_count,omitempty"`
}

func (m *ListBacklogReviewsProxyResponse) Reset()         { *m = ListBacklogReviewsProxyResponse{} }
func (m *ListBacklogReviewsProxyResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *ListBacklogReviewsProxyResponse) ProtoMessage()  {}

// --- Backlog review shared message types ---

type BacklogReviewMsgWire struct {
	CeremonyID  string                      `protobuf:"bytes,1,opt,name=ceremony_id,json=ceremonyId" json:"ceremony_id,omitempty"`
	StoryIDs    []string                    `protobuf:"bytes,2,rep,name=story_ids,json=storyIds" json:"story_ids,omitempty"`
	Status      string                      `protobuf:"bytes,3,opt,name=status" json:"status,omitempty"`
	ReviewResults []*StoryReviewResultMsgWire `protobuf:"bytes,4,rep,name=review_results,json=reviewResults" json:"review_results,omitempty"`
	CreatedBy   string                      `protobuf:"bytes,5,opt,name=created_by,json=createdBy" json:"created_by,omitempty"`
	CreatedAt   string                      `protobuf:"bytes,6,opt,name=created_at,json=createdAt" json:"created_at,omitempty"`
	UpdatedAt   string                      `protobuf:"bytes,7,opt,name=updated_at,json=updatedAt" json:"updated_at,omitempty"`
	StartedAt   string                      `protobuf:"bytes,8,opt,name=started_at,json=startedAt" json:"started_at,omitempty"`
	CompletedAt string                      `protobuf:"bytes,9,opt,name=completed_at,json=completedAt" json:"completed_at,omitempty"`
}

func (m *BacklogReviewMsgWire) Reset()         { *m = BacklogReviewMsgWire{} }
func (m *BacklogReviewMsgWire) String() string { return fmt.Sprintf("%+v", *m) }
func (m *BacklogReviewMsgWire) ProtoMessage()  {}

type StoryReviewResultMsgWire struct {
	StoryID            string                  `protobuf:"bytes,1,opt,name=story_id,json=storyId" json:"story_id,omitempty"`
	PlanPreliminary    *PlanPreliminaryMsgWire `protobuf:"bytes,2,opt,name=plan_preliminary,json=planPreliminary" json:"plan_preliminary,omitempty"`
	ArchitectFeedback  string                  `protobuf:"bytes,3,opt,name=architect_feedback,json=architectFeedback" json:"architect_feedback,omitempty"`
	QAFeedback         string                  `protobuf:"bytes,4,opt,name=qa_feedback,json=qaFeedback" json:"qa_feedback,omitempty"`
	DevopsFeedback     string                  `protobuf:"bytes,5,opt,name=devops_feedback,json=devopsFeedback" json:"devops_feedback,omitempty"`
	Recommendations    []string                `protobuf:"bytes,6,rep,name=recommendations" json:"recommendations,omitempty"`
	ApprovalStatus     string                  `protobuf:"bytes,7,opt,name=approval_status,json=approvalStatus" json:"approval_status,omitempty"`
	ReviewedAt         string                  `protobuf:"bytes,8,opt,name=reviewed_at,json=reviewedAt" json:"reviewed_at,omitempty"`
	ApprovedBy         string                  `protobuf:"bytes,9,opt,name=approved_by,json=approvedBy" json:"approved_by,omitempty"`
	ApprovedAt         string                  `protobuf:"bytes,10,opt,name=approved_at,json=approvedAt" json:"approved_at,omitempty"`
	RejectedBy         string                  `protobuf:"bytes,11,opt,name=rejected_by,json=rejectedBy" json:"rejected_by,omitempty"`
	RejectedAt         string                  `protobuf:"bytes,12,opt,name=rejected_at,json=rejectedAt" json:"rejected_at,omitempty"`
	RejectionReason    string                  `protobuf:"bytes,13,opt,name=rejection_reason,json=rejectionReason" json:"rejection_reason,omitempty"`
	PONotes            string                  `protobuf:"bytes,14,opt,name=po_notes,json=poNotes" json:"po_notes,omitempty"`
	POConcerns         string                  `protobuf:"bytes,15,opt,name=po_concerns,json=poConcerns" json:"po_concerns,omitempty"`
	PriorityAdjustment string                  `protobuf:"bytes,16,opt,name=priority_adjustment,json=priorityAdjustment" json:"priority_adjustment,omitempty"`
	POPriorityReason   string                  `protobuf:"bytes,17,opt,name=po_priority_reason,json=poPriorityReason" json:"po_priority_reason,omitempty"`
	PlanID             string                  `protobuf:"bytes,18,opt,name=plan_id,json=planId" json:"plan_id,omitempty"`
}

func (m *StoryReviewResultMsgWire) Reset()         { *m = StoryReviewResultMsgWire{} }
func (m *StoryReviewResultMsgWire) String() string { return fmt.Sprintf("%+v", *m) }
func (m *StoryReviewResultMsgWire) ProtoMessage()  {}

type PlanPreliminaryMsgWire struct {
	Title               string   `protobuf:"bytes,1,opt,name=title" json:"title,omitempty"`
	Description         string   `protobuf:"bytes,2,opt,name=description" json:"description,omitempty"`
	AcceptanceCriteria  []string `protobuf:"bytes,3,rep,name=acceptance_criteria,json=acceptanceCriteria" json:"acceptance_criteria,omitempty"`
	TechnicalNotes      string   `protobuf:"bytes,4,opt,name=technical_notes,json=technicalNotes" json:"technical_notes,omitempty"`
	Roles               []string `protobuf:"bytes,5,rep,name=roles" json:"roles,omitempty"`
	EstimatedComplexity string   `protobuf:"bytes,6,opt,name=estimated_complexity,json=estimatedComplexity" json:"estimated_complexity,omitempty"`
	Dependencies        []string `protobuf:"bytes,7,rep,name=dependencies" json:"dependencies,omitempty"`
	TasksOutline        []string `protobuf:"bytes,8,rep,name=tasks_outline,json=tasksOutline" json:"tasks_outline,omitempty"`
}

func (m *PlanPreliminaryMsgWire) Reset()         { *m = PlanPreliminaryMsgWire{} }
func (m *PlanPreliminaryMsgWire) String() string { return fmt.Sprintf("%+v", *m) }
func (m *PlanPreliminaryMsgWire) ProtoMessage()  {}

// --- Ceremony instance query types ---

type GetCeremonyInstanceRequest struct {
	InstanceID string `protobuf:"bytes,1,opt,name=instance_id,json=instanceId" json:"instance_id,omitempty"`
}

func (m *GetCeremonyInstanceRequest) Reset()         { *m = GetCeremonyInstanceRequest{} }
func (m *GetCeremonyInstanceRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *GetCeremonyInstanceRequest) ProtoMessage()  {}

type CeremonyInstanceResponse struct {
	Ceremony *CeremonyInstanceMsg `protobuf:"bytes,1,opt,name=ceremony" json:"ceremony,omitempty"`
}

func (m *CeremonyInstanceResponse) Reset()         { *m = CeremonyInstanceResponse{} }
func (m *CeremonyInstanceResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *CeremonyInstanceResponse) ProtoMessage()  {}

type CeremonyInstanceMsg struct {
	InstanceID     string            `protobuf:"bytes,1,opt,name=instance_id,json=instanceId" json:"instance_id,omitempty"`
	CeremonyID     string            `protobuf:"bytes,2,opt,name=ceremony_id,json=ceremonyId" json:"ceremony_id,omitempty"`
	StoryID        string            `protobuf:"bytes,3,opt,name=story_id,json=storyId" json:"story_id,omitempty"`
	DefinitionName string            `protobuf:"bytes,4,opt,name=definition_name,json=definitionName" json:"definition_name,omitempty"`
	CurrentState   string            `protobuf:"bytes,5,opt,name=current_state,json=currentState" json:"current_state,omitempty"`
	Status         string            `protobuf:"bytes,6,opt,name=status" json:"status,omitempty"`
	CorrelationID  string            `protobuf:"bytes,7,opt,name=correlation_id,json=correlationId" json:"correlation_id,omitempty"`
	StepStatus     map[string]string `protobuf:"bytes,8,rep,name=step_status,json=stepStatus" protobuf_key:"bytes,1,opt,name=key" protobuf_val:"bytes,2,opt,name=value" json:"step_status,omitempty"`
	StepOutputs    map[string]string `protobuf:"bytes,9,rep,name=step_outputs,json=stepOutputs" protobuf_key:"bytes,1,opt,name=key" protobuf_val:"bytes,2,opt,name=value" json:"step_outputs,omitempty"`
	CreatedAt      string            `protobuf:"bytes,10,opt,name=created_at,json=createdAt" json:"created_at,omitempty"`
	UpdatedAt      string            `protobuf:"bytes,11,opt,name=updated_at,json=updatedAt" json:"updated_at,omitempty"`
}

func (m *CeremonyInstanceMsg) Reset()         { *m = CeremonyInstanceMsg{} }
func (m *CeremonyInstanceMsg) String() string { return fmt.Sprintf("%+v", *m) }
func (m *CeremonyInstanceMsg) ProtoMessage()  {}

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

type ListCeremonyInstancesResponse struct {
	Ceremonies []*CeremonyInstanceMsg `protobuf:"bytes,1,rep,name=ceremonies" json:"ceremonies,omitempty"`
	TotalCount int32                  `protobuf:"varint,2,opt,name=total_count,json=totalCount" json:"total_count,omitempty"`
}

func (m *ListCeremonyInstancesResponse) Reset()         { *m = ListCeremonyInstancesResponse{} }
func (m *ListCeremonyInstancesResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *ListCeremonyInstancesResponse) ProtoMessage()  {}