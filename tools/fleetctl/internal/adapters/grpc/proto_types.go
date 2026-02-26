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