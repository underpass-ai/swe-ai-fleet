// Package grpcapi provides the gRPC server adapter for the fleet-proxy.
// This file implements the FleetCommandService, translating incoming gRPC
// requests into application-layer command handler calls.
//
// Since the fleet-proxy does not import generated proto stubs from another
// module, request/response types are defined here as plain structs that
// implement the legacy proto.Message interface (Reset, String, ProtoMessage).
// The gRPC codec handles these via reflection-based protobuf encoding using
// the struct tags. When proto code generation is added to this module, these
// types will be replaced by the generated ones.
package grpcapi

import (
	"context"
	"fmt"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/adapters/grpcapi/interceptors"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/command"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

// ---------------------------------------------------------------------------
// Request / Response types matching fleet.proxy.v1.FleetCommandService proto.
// Each type implements Reset(), String(), and ProtoMessage() so that the gRPC
// proto codec can marshal/unmarshal them via legacy reflection.
// ---------------------------------------------------------------------------

// CreateProjectRequest mirrors fleet.proxy.v1.CreateProjectRequest.
type CreateProjectRequest struct {
	RequestID   string `protobuf:"bytes,1,opt,name=request_id,json=requestId" json:"request_id,omitempty"`
	Name        string `protobuf:"bytes,2,opt,name=name" json:"name,omitempty"`
	Description string `protobuf:"bytes,3,opt,name=description" json:"description,omitempty"`
}

func (m *CreateProjectRequest) Reset()         { *m = CreateProjectRequest{} }
func (m *CreateProjectRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *CreateProjectRequest) ProtoMessage()  {}

// CreateProjectResponse mirrors fleet.proxy.v1.CreateProjectResponse.
type CreateProjectResponse struct {
	ProjectID string `protobuf:"bytes,1,opt,name=project_id,json=projectId" json:"project_id,omitempty"`
	Success   bool   `protobuf:"varint,2,opt,name=success" json:"success,omitempty"`
	Message   string `protobuf:"bytes,3,opt,name=message" json:"message,omitempty"`
}

func (m *CreateProjectResponse) Reset()         { *m = CreateProjectResponse{} }
func (m *CreateProjectResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *CreateProjectResponse) ProtoMessage()  {}

// CreateEpicRequest mirrors fleet.proxy.v1.CreateEpicRequest.
type CreateEpicRequest struct {
	RequestID   string `protobuf:"bytes,1,opt,name=request_id,json=requestId" json:"request_id,omitempty"`
	ProjectID   string `protobuf:"bytes,2,opt,name=project_id,json=projectId" json:"project_id,omitempty"`
	Title       string `protobuf:"bytes,3,opt,name=title" json:"title,omitempty"`
	Description string `protobuf:"bytes,4,opt,name=description" json:"description,omitempty"`
}

func (m *CreateEpicRequest) Reset()         { *m = CreateEpicRequest{} }
func (m *CreateEpicRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *CreateEpicRequest) ProtoMessage()  {}

// CreateEpicResponse mirrors fleet.proxy.v1.CreateEpicResponse.
type CreateEpicResponse struct {
	EpicID  string `protobuf:"bytes,1,opt,name=epic_id,json=epicId" json:"epic_id,omitempty"`
	Success bool   `protobuf:"varint,2,opt,name=success" json:"success,omitempty"`
	Message string `protobuf:"bytes,3,opt,name=message" json:"message,omitempty"`
}

func (m *CreateEpicResponse) Reset()         { *m = CreateEpicResponse{} }
func (m *CreateEpicResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *CreateEpicResponse) ProtoMessage()  {}

// CreateStoryRequest mirrors fleet.proxy.v1.CreateStoryRequest.
type CreateStoryRequest struct {
	RequestID string `protobuf:"bytes,1,opt,name=request_id,json=requestId" json:"request_id,omitempty"`
	EpicID    string `protobuf:"bytes,2,opt,name=epic_id,json=epicId" json:"epic_id,omitempty"`
	Title     string `protobuf:"bytes,3,opt,name=title" json:"title,omitempty"`
	Brief     string `protobuf:"bytes,4,opt,name=brief" json:"brief,omitempty"`
}

func (m *CreateStoryRequest) Reset()         { *m = CreateStoryRequest{} }
func (m *CreateStoryRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *CreateStoryRequest) ProtoMessage()  {}

// CreateStoryResponse mirrors fleet.proxy.v1.CreateStoryResponse.
type CreateStoryResponse struct {
	StoryID string `protobuf:"bytes,1,opt,name=story_id,json=storyId" json:"story_id,omitempty"`
	Success bool   `protobuf:"varint,2,opt,name=success" json:"success,omitempty"`
	Message string `protobuf:"bytes,3,opt,name=message" json:"message,omitempty"`
}

func (m *CreateStoryResponse) Reset()         { *m = CreateStoryResponse{} }
func (m *CreateStoryResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *CreateStoryResponse) ProtoMessage()  {}

// TransitionStoryRequest mirrors fleet.proxy.v1.TransitionStoryRequest.
type TransitionStoryRequest struct {
	StoryID     string `protobuf:"bytes,1,opt,name=story_id,json=storyId" json:"story_id,omitempty"`
	TargetState string `protobuf:"bytes,2,opt,name=target_state,json=targetState" json:"target_state,omitempty"`
}

func (m *TransitionStoryRequest) Reset()         { *m = TransitionStoryRequest{} }
func (m *TransitionStoryRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *TransitionStoryRequest) ProtoMessage()  {}

// TransitionStoryResponse mirrors fleet.proxy.v1.TransitionStoryResponse.
type TransitionStoryResponse struct {
	Success bool   `protobuf:"varint,1,opt,name=success" json:"success,omitempty"`
	Message string `protobuf:"bytes,2,opt,name=message" json:"message,omitempty"`
}

func (m *TransitionStoryResponse) Reset()         { *m = TransitionStoryResponse{} }
func (m *TransitionStoryResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *TransitionStoryResponse) ProtoMessage()  {}

// CreateTaskRequest mirrors fleet.proxy.v1.CreateTaskRequest.
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

// CreateTaskResponse mirrors fleet.proxy.v1.CreateTaskResponse.
type CreateTaskResponse struct {
	TaskID  string `protobuf:"bytes,1,opt,name=task_id,json=taskId" json:"task_id,omitempty"`
	Success bool   `protobuf:"varint,2,opt,name=success" json:"success,omitempty"`
	Message string `protobuf:"bytes,3,opt,name=message" json:"message,omitempty"`
}

func (m *CreateTaskResponse) Reset()         { *m = CreateTaskResponse{} }
func (m *CreateTaskResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *CreateTaskResponse) ProtoMessage()  {}

// StartPlanningCeremonyRequest mirrors fleet.proxy.v1.StartPlanningCeremonyRequest.
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

// StartPlanningCeremonyResponse mirrors fleet.proxy.v1.StartPlanningCeremonyResponse.
type StartPlanningCeremonyResponse struct {
	InstanceID string `protobuf:"bytes,1,opt,name=instance_id,json=instanceId" json:"instance_id,omitempty"`
	Status     string `protobuf:"bytes,2,opt,name=status" json:"status,omitempty"`
	Message    string `protobuf:"bytes,3,opt,name=message" json:"message,omitempty"`
}

func (m *StartPlanningCeremonyResponse) Reset()         { *m = StartPlanningCeremonyResponse{} }
func (m *StartPlanningCeremonyResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *StartPlanningCeremonyResponse) ProtoMessage()  {}

// ---------------------------------------------------------------------------
// Shared wire types for backlog review messages
// ---------------------------------------------------------------------------

// BacklogReviewMsgWire mirrors fleet.proxy.v1.BacklogReviewCeremony.
type BacklogReviewMsgWire struct {
	CeremonyID    string                    `protobuf:"bytes,1,opt,name=ceremony_id,json=ceremonyId" json:"ceremony_id,omitempty"`
	StoryIDs      []string                  `protobuf:"bytes,2,rep,name=story_ids,json=storyIds" json:"story_ids,omitempty"`
	Status        string                    `protobuf:"bytes,3,opt,name=status" json:"status,omitempty"`
	ReviewResults []*StoryReviewResultMsgWire `protobuf:"bytes,4,rep,name=review_results,json=reviewResults" json:"review_results,omitempty"`
	CreatedBy     string                    `protobuf:"bytes,5,opt,name=created_by,json=createdBy" json:"created_by,omitempty"`
	CreatedAt     string                    `protobuf:"bytes,6,opt,name=created_at,json=createdAt" json:"created_at,omitempty"`
	UpdatedAt     string                    `protobuf:"bytes,7,opt,name=updated_at,json=updatedAt" json:"updated_at,omitempty"`
	StartedAt     string                    `protobuf:"bytes,8,opt,name=started_at,json=startedAt" json:"started_at,omitempty"`
	CompletedAt   string                    `protobuf:"bytes,9,opt,name=completed_at,json=completedAt" json:"completed_at,omitempty"`
}

func (m *BacklogReviewMsgWire) Reset()         { *m = BacklogReviewMsgWire{} }
func (m *BacklogReviewMsgWire) String() string { return fmt.Sprintf("%+v", *m) }
func (m *BacklogReviewMsgWire) ProtoMessage()  {}

// StoryReviewResultMsgWire mirrors fleet.proxy.v1.StoryReviewResult.
type StoryReviewResultMsgWire struct {
	StoryID            string                `protobuf:"bytes,1,opt,name=story_id,json=storyId" json:"story_id,omitempty"`
	PlanPreliminary    *PlanPreliminaryMsgWire `protobuf:"bytes,2,opt,name=plan_preliminary,json=planPreliminary" json:"plan_preliminary,omitempty"`
	ArchitectFeedback  string                `protobuf:"bytes,3,opt,name=architect_feedback,json=architectFeedback" json:"architect_feedback,omitempty"`
	QAFeedback         string                `protobuf:"bytes,4,opt,name=qa_feedback,json=qaFeedback" json:"qa_feedback,omitempty"`
	DevopsFeedback     string                `protobuf:"bytes,5,opt,name=devops_feedback,json=devopsFeedback" json:"devops_feedback,omitempty"`
	Recommendations    []string              `protobuf:"bytes,6,rep,name=recommendations" json:"recommendations,omitempty"`
	ApprovalStatus     string                `protobuf:"bytes,7,opt,name=approval_status,json=approvalStatus" json:"approval_status,omitempty"`
	ReviewedAt         string                `protobuf:"bytes,8,opt,name=reviewed_at,json=reviewedAt" json:"reviewed_at,omitempty"`
	ApprovedBy         string                `protobuf:"bytes,9,opt,name=approved_by,json=approvedBy" json:"approved_by,omitempty"`
	ApprovedAt         string                `protobuf:"bytes,10,opt,name=approved_at,json=approvedAt" json:"approved_at,omitempty"`
	RejectedBy         string                `protobuf:"bytes,11,opt,name=rejected_by,json=rejectedBy" json:"rejected_by,omitempty"`
	RejectedAt         string                `protobuf:"bytes,12,opt,name=rejected_at,json=rejectedAt" json:"rejected_at,omitempty"`
	RejectionReason    string                `protobuf:"bytes,13,opt,name=rejection_reason,json=rejectionReason" json:"rejection_reason,omitempty"`
	PONotes            string                `protobuf:"bytes,14,opt,name=po_notes,json=poNotes" json:"po_notes,omitempty"`
	POConcerns         string                `protobuf:"bytes,15,opt,name=po_concerns,json=poConcerns" json:"po_concerns,omitempty"`
	PriorityAdjustment string                `protobuf:"bytes,16,opt,name=priority_adjustment,json=priorityAdjustment" json:"priority_adjustment,omitempty"`
	POPriorityReason   string                `protobuf:"bytes,17,opt,name=po_priority_reason,json=poPriorityReason" json:"po_priority_reason,omitempty"`
	PlanID             string                `protobuf:"bytes,18,opt,name=plan_id,json=planId" json:"plan_id,omitempty"`
}

func (m *StoryReviewResultMsgWire) Reset()         { *m = StoryReviewResultMsgWire{} }
func (m *StoryReviewResultMsgWire) String() string { return fmt.Sprintf("%+v", *m) }
func (m *StoryReviewResultMsgWire) ProtoMessage()  {}

// PlanPreliminaryMsgWire mirrors fleet.proxy.v1.PlanPreliminary.
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

// ---------------------------------------------------------------------------
// Backlog review command request/response types
// ---------------------------------------------------------------------------

// StartBacklogReviewRequest mirrors fleet.proxy.v1.StartBacklogReviewRequest.
type StartBacklogReviewRequest struct {
	RequestID  string `protobuf:"bytes,1,opt,name=request_id,json=requestId" json:"request_id,omitempty"`
	CeremonyID string `protobuf:"bytes,2,opt,name=ceremony_id,json=ceremonyId" json:"ceremony_id,omitempty"`
}

func (m *StartBacklogReviewRequest) Reset()         { *m = StartBacklogReviewRequest{} }
func (m *StartBacklogReviewRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *StartBacklogReviewRequest) ProtoMessage()  {}

// StartBacklogReviewResponse mirrors fleet.proxy.v1.StartBacklogReviewResponse.
type StartBacklogReviewResponse struct {
	Ceremony                    *BacklogReviewMsgWire `protobuf:"bytes,1,opt,name=ceremony" json:"ceremony,omitempty"`
	Success                     bool                  `protobuf:"varint,2,opt,name=success" json:"success,omitempty"`
	Message                     string                `protobuf:"bytes,3,opt,name=message" json:"message,omitempty"`
	TotalDeliberationsSubmitted int32                 `protobuf:"varint,4,opt,name=total_deliberations_submitted,json=totalDeliberationsSubmitted" json:"total_deliberations_submitted,omitempty"`
}

func (m *StartBacklogReviewResponse) Reset()         { *m = StartBacklogReviewResponse{} }
func (m *StartBacklogReviewResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *StartBacklogReviewResponse) ProtoMessage()  {}

// CreateBacklogReviewRequest mirrors fleet.proxy.v1.CreateBacklogReviewRequest.
type CreateBacklogReviewRequest struct {
	RequestID string   `protobuf:"bytes,1,opt,name=request_id,json=requestId" json:"request_id,omitempty"`
	StoryIDs  []string `protobuf:"bytes,2,rep,name=story_ids,json=storyIds" json:"story_ids,omitempty"`
}

func (m *CreateBacklogReviewRequest) Reset()         { *m = CreateBacklogReviewRequest{} }
func (m *CreateBacklogReviewRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *CreateBacklogReviewRequest) ProtoMessage()  {}

// CreateBacklogReviewResponse mirrors fleet.proxy.v1.CreateBacklogReviewResponse.
type CreateBacklogReviewResponse struct {
	Ceremony *BacklogReviewMsgWire `protobuf:"bytes,1,opt,name=ceremony" json:"ceremony,omitempty"`
	Success  bool                  `protobuf:"varint,2,opt,name=success" json:"success,omitempty"`
	Message  string                `protobuf:"bytes,3,opt,name=message" json:"message,omitempty"`
}

func (m *CreateBacklogReviewResponse) Reset()         { *m = CreateBacklogReviewResponse{} }
func (m *CreateBacklogReviewResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *CreateBacklogReviewResponse) ProtoMessage()  {}

// ApproveReviewPlanProxyRequest mirrors fleet.proxy.v1.ApproveReviewPlanRequest.
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

// ApproveReviewPlanProxyResponse mirrors fleet.proxy.v1.ApproveReviewPlanResponse.
type ApproveReviewPlanProxyResponse struct {
	Ceremony *BacklogReviewMsgWire `protobuf:"bytes,1,opt,name=ceremony" json:"ceremony,omitempty"`
	PlanID   string                `protobuf:"bytes,2,opt,name=plan_id,json=planId" json:"plan_id,omitempty"`
	Success  bool                  `protobuf:"varint,3,opt,name=success" json:"success,omitempty"`
	Message  string                `protobuf:"bytes,4,opt,name=message" json:"message,omitempty"`
}

func (m *ApproveReviewPlanProxyResponse) Reset()         { *m = ApproveReviewPlanProxyResponse{} }
func (m *ApproveReviewPlanProxyResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *ApproveReviewPlanProxyResponse) ProtoMessage()  {}

// RejectReviewPlanProxyRequest mirrors fleet.proxy.v1.RejectReviewPlanRequest.
type RejectReviewPlanProxyRequest struct {
	CeremonyID string `protobuf:"bytes,1,opt,name=ceremony_id,json=ceremonyId" json:"ceremony_id,omitempty"`
	StoryID    string `protobuf:"bytes,2,opt,name=story_id,json=storyId" json:"story_id,omitempty"`
	Reason     string `protobuf:"bytes,3,opt,name=reason" json:"reason,omitempty"`
}

func (m *RejectReviewPlanProxyRequest) Reset()         { *m = RejectReviewPlanProxyRequest{} }
func (m *RejectReviewPlanProxyRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *RejectReviewPlanProxyRequest) ProtoMessage()  {}

// RejectReviewPlanProxyResponse mirrors fleet.proxy.v1.RejectReviewPlanResponse.
type RejectReviewPlanProxyResponse struct {
	Ceremony *BacklogReviewMsgWire `protobuf:"bytes,1,opt,name=ceremony" json:"ceremony,omitempty"`
	Success  bool                  `protobuf:"varint,2,opt,name=success" json:"success,omitempty"`
	Message  string                `protobuf:"bytes,3,opt,name=message" json:"message,omitempty"`
}

func (m *RejectReviewPlanProxyResponse) Reset()         { *m = RejectReviewPlanProxyResponse{} }
func (m *RejectReviewPlanProxyResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *RejectReviewPlanProxyResponse) ProtoMessage()  {}

// CompleteBacklogReviewRequest mirrors fleet.proxy.v1.CompleteBacklogReviewRequest.
type CompleteBacklogReviewRequest struct {
	CeremonyID string `protobuf:"bytes,1,opt,name=ceremony_id,json=ceremonyId" json:"ceremony_id,omitempty"`
}

func (m *CompleteBacklogReviewRequest) Reset()         { *m = CompleteBacklogReviewRequest{} }
func (m *CompleteBacklogReviewRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *CompleteBacklogReviewRequest) ProtoMessage()  {}

// CompleteBacklogReviewResponse mirrors fleet.proxy.v1.CompleteBacklogReviewResponse.
type CompleteBacklogReviewResponse struct {
	Ceremony *BacklogReviewMsgWire `protobuf:"bytes,1,opt,name=ceremony" json:"ceremony,omitempty"`
	Success  bool                  `protobuf:"varint,2,opt,name=success" json:"success,omitempty"`
	Message  string                `protobuf:"bytes,3,opt,name=message" json:"message,omitempty"`
}

func (m *CompleteBacklogReviewResponse) Reset()         { *m = CompleteBacklogReviewResponse{} }
func (m *CompleteBacklogReviewResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *CompleteBacklogReviewResponse) ProtoMessage()  {}

// CancelBacklogReviewRequest mirrors fleet.proxy.v1.CancelBacklogReviewRequest.
type CancelBacklogReviewRequest struct {
	CeremonyID string `protobuf:"bytes,1,opt,name=ceremony_id,json=ceremonyId" json:"ceremony_id,omitempty"`
}

func (m *CancelBacklogReviewRequest) Reset()         { *m = CancelBacklogReviewRequest{} }
func (m *CancelBacklogReviewRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *CancelBacklogReviewRequest) ProtoMessage()  {}

// CancelBacklogReviewResponse mirrors fleet.proxy.v1.CancelBacklogReviewResponse.
type CancelBacklogReviewResponse struct {
	Ceremony *BacklogReviewMsgWire `protobuf:"bytes,1,opt,name=ceremony" json:"ceremony,omitempty"`
	Success  bool                  `protobuf:"varint,2,opt,name=success" json:"success,omitempty"`
	Message  string                `protobuf:"bytes,3,opt,name=message" json:"message,omitempty"`
}

func (m *CancelBacklogReviewResponse) Reset()         { *m = CancelBacklogReviewResponse{} }
func (m *CancelBacklogReviewResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *CancelBacklogReviewResponse) ProtoMessage()  {}

// ApproveDecisionRequest mirrors fleet.proxy.v1.ApproveDecisionRequest.
type ApproveDecisionRequest struct {
	StoryID    string `protobuf:"bytes,1,opt,name=story_id,json=storyId" json:"story_id,omitempty"`
	DecisionID string `protobuf:"bytes,2,opt,name=decision_id,json=decisionId" json:"decision_id,omitempty"`
	Comment    string `protobuf:"bytes,3,opt,name=comment" json:"comment,omitempty"`
}

func (m *ApproveDecisionRequest) Reset()         { *m = ApproveDecisionRequest{} }
func (m *ApproveDecisionRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *ApproveDecisionRequest) ProtoMessage()  {}

// ApproveDecisionResponse mirrors fleet.proxy.v1.ApproveDecisionResponse.
type ApproveDecisionResponse struct {
	Success bool   `protobuf:"varint,1,opt,name=success" json:"success,omitempty"`
	Message string `protobuf:"bytes,2,opt,name=message" json:"message,omitempty"`
}

func (m *ApproveDecisionResponse) Reset()         { *m = ApproveDecisionResponse{} }
func (m *ApproveDecisionResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *ApproveDecisionResponse) ProtoMessage()  {}

// RejectDecisionRequest mirrors fleet.proxy.v1.RejectDecisionRequest.
type RejectDecisionRequest struct {
	StoryID    string `protobuf:"bytes,1,opt,name=story_id,json=storyId" json:"story_id,omitempty"`
	DecisionID string `protobuf:"bytes,2,opt,name=decision_id,json=decisionId" json:"decision_id,omitempty"`
	Reason     string `protobuf:"bytes,3,opt,name=reason" json:"reason,omitempty"`
}

func (m *RejectDecisionRequest) Reset()         { *m = RejectDecisionRequest{} }
func (m *RejectDecisionRequest) String() string { return fmt.Sprintf("%+v", *m) }
func (m *RejectDecisionRequest) ProtoMessage()  {}

// RejectDecisionResponse mirrors fleet.proxy.v1.RejectDecisionResponse.
type RejectDecisionResponse struct {
	Success bool   `protobuf:"varint,1,opt,name=success" json:"success,omitempty"`
	Message string `protobuf:"bytes,2,opt,name=message" json:"message,omitempty"`
}

func (m *RejectDecisionResponse) Reset()         { *m = RejectDecisionResponse{} }
func (m *RejectDecisionResponse) String() string { return fmt.Sprintf("%+v", *m) }
func (m *RejectDecisionResponse) ProtoMessage()  {}

// ---------------------------------------------------------------------------
// FleetCommandService implementation
// ---------------------------------------------------------------------------

// FleetCommandService handles write-side gRPC RPCs by delegating to the
// application-layer command handlers. It extracts the caller identity from the
// gRPC context (populated by the auth interceptor) and passes it along.
type FleetCommandService struct {
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

// HandleCreateProject handles the CreateProject RPC.
func (s *FleetCommandService) HandleCreateProject(ctx context.Context, req *CreateProjectRequest) (*CreateProjectResponse, error) {
	clientID := interceptors.ClientIDFromContext(ctx)

	projectID, err := s.createProject.Handle(ctx, command.CreateProjectCmd{
		RequestID:   req.RequestID,
		Name:        req.Name,
		Description: req.Description,
		RequestedBy: clientID,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "create project: %v", err)
	}

	return &CreateProjectResponse{
		ProjectID: projectID,
		Success:   true,
		Message:   "project created",
	}, nil
}

// HandleCreateEpic handles the CreateEpic RPC.
func (s *FleetCommandService) HandleCreateEpic(ctx context.Context, req *CreateEpicRequest) (*CreateEpicResponse, error) {
	clientID := interceptors.ClientIDFromContext(ctx)

	epicID, err := s.createEpic.Handle(ctx, command.CreateEpicCmd{
		RequestID:   req.RequestID,
		ProjectID:   req.ProjectID,
		Title:       req.Title,
		Description: req.Description,
		RequestedBy: clientID,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "create epic: %v", err)
	}

	return &CreateEpicResponse{
		EpicID:  epicID,
		Success: true,
		Message: "epic created",
	}, nil
}

// HandleCreateStory handles the CreateStory RPC.
func (s *FleetCommandService) HandleCreateStory(ctx context.Context, req *CreateStoryRequest) (*CreateStoryResponse, error) {
	clientID := interceptors.ClientIDFromContext(ctx)

	storyID, err := s.createStory.Handle(ctx, command.CreateStoryCmd{
		RequestID:   req.RequestID,
		EpicID:      req.EpicID,
		Title:       req.Title,
		Brief:       req.Brief,
		RequestedBy: clientID,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "create story: %v", err)
	}

	return &CreateStoryResponse{
		StoryID: storyID,
		Success: true,
		Message: "story created",
	}, nil
}

// HandleTransitionStory handles the TransitionStory RPC.
func (s *FleetCommandService) HandleTransitionStory(ctx context.Context, req *TransitionStoryRequest) (*TransitionStoryResponse, error) {
	clientID := interceptors.ClientIDFromContext(ctx)

	err := s.transitionStory.Handle(ctx, command.TransitionStoryCmd{
		StoryID:     req.StoryID,
		TargetState: req.TargetState,
		RequestedBy: clientID,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "transition story: %v", err)
	}

	return &TransitionStoryResponse{
		Success: true,
		Message: "story transitioned",
	}, nil
}

// HandleCreateTask handles the CreateTask RPC.
func (s *FleetCommandService) HandleCreateTask(ctx context.Context, req *CreateTaskRequest) (*CreateTaskResponse, error) {
	clientID := interceptors.ClientIDFromContext(ctx)

	taskID, err := s.createTask.Handle(ctx, command.CreateTaskCmd{
		RequestID:      req.RequestID,
		StoryID:        req.StoryID,
		Title:          req.Title,
		Description:    req.Description,
		Type:           req.Type,
		AssignedTo:     req.AssignedTo,
		EstimatedHours: req.EstimatedHours,
		Priority:       req.Priority,
		RequestedBy:    clientID,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "create task: %v", err)
	}

	return &CreateTaskResponse{
		TaskID:  taskID,
		Success: true,
		Message: "task created",
	}, nil
}

// HandleStartPlanningCeremony handles the StartPlanningCeremony RPC.
func (s *FleetCommandService) HandleStartPlanningCeremony(ctx context.Context, req *StartPlanningCeremonyRequest) (*StartPlanningCeremonyResponse, error) {
	clientID := interceptors.ClientIDFromContext(ctx)

	instanceID, err := s.startCeremony.Handle(ctx, command.StartCeremonyCmd{
		RequestID:      req.RequestID,
		CeremonyID:     req.CeremonyID,
		DefinitionName: req.DefinitionName,
		StoryID:        req.StoryID,
		StepIDs:        req.StepIDs,
		RequestedBy:    clientID,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "start planning ceremony: %v", err)
	}

	return &StartPlanningCeremonyResponse{
		InstanceID: instanceID,
		Status:     "started",
		Message:    "ceremony started",
	}, nil
}

// HandleStartBacklogReview handles the StartBacklogReview RPC.
func (s *FleetCommandService) HandleStartBacklogReview(ctx context.Context, req *StartBacklogReviewRequest) (*StartBacklogReviewResponse, error) {
	clientID := interceptors.ClientIDFromContext(ctx)

	result, reviewCount, err := s.startBacklogReview.Handle(ctx, command.StartBacklogReviewCmd{
		RequestID:   req.RequestID,
		CeremonyID:  req.CeremonyID,
		RequestedBy: clientID,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "start backlog review: %v", err)
	}

	return &StartBacklogReviewResponse{
		Ceremony:                    backlogReviewResultToWire(result),
		Success:                     true,
		Message:                     "backlog review started",
		TotalDeliberationsSubmitted: reviewCount,
	}, nil
}

// HandleCreateBacklogReview handles the CreateBacklogReview RPC.
func (s *FleetCommandService) HandleCreateBacklogReview(ctx context.Context, req *CreateBacklogReviewRequest) (*CreateBacklogReviewResponse, error) {
	clientID := interceptors.ClientIDFromContext(ctx)

	result, err := s.createBacklogReview.Handle(ctx, command.CreateBacklogReviewCmd{
		RequestID:   req.RequestID,
		RequestedBy: clientID,
		StoryIDs:    req.StoryIDs,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "create backlog review: %v", err)
	}

	return &CreateBacklogReviewResponse{
		Ceremony: backlogReviewResultToWire(result),
		Success:  true,
		Message:  "backlog review created",
	}, nil
}

// HandleApproveReviewPlan handles the ApproveReviewPlan RPC.
func (s *FleetCommandService) HandleApproveReviewPlan(ctx context.Context, req *ApproveReviewPlanProxyRequest) (*ApproveReviewPlanProxyResponse, error) {
	clientID := interceptors.ClientIDFromContext(ctx)

	result, planID, err := s.approveReviewPlan.Handle(ctx, command.ApproveReviewPlanCmd{
		RequestID:          req.CeremonyID, // use ceremonyID as request ID for idempotency
		CeremonyID:         req.CeremonyID,
		StoryID:            req.StoryID,
		PONotes:            req.PONotes,
		POConcerns:         req.POConcerns,
		PriorityAdjustment: req.PriorityAdjustment,
		POPriorityReason:   req.POPriorityReason,
		RequestedBy:        clientID,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "approve review plan: %v", err)
	}

	return &ApproveReviewPlanProxyResponse{
		Ceremony: backlogReviewResultToWire(result),
		PlanID:   planID,
		Success:  true,
		Message:  "review plan approved",
	}, nil
}

// HandleRejectReviewPlan handles the RejectReviewPlan RPC.
func (s *FleetCommandService) HandleRejectReviewPlan(ctx context.Context, req *RejectReviewPlanProxyRequest) (*RejectReviewPlanProxyResponse, error) {
	clientID := interceptors.ClientIDFromContext(ctx)

	result, err := s.rejectReviewPlan.Handle(ctx, command.RejectReviewPlanCmd{
		RequestID:   req.CeremonyID,
		CeremonyID:  req.CeremonyID,
		StoryID:     req.StoryID,
		Reason:      req.Reason,
		RequestedBy: clientID,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "reject review plan: %v", err)
	}

	return &RejectReviewPlanProxyResponse{
		Ceremony: backlogReviewResultToWire(result),
		Success:  true,
		Message:  "review plan rejected",
	}, nil
}

// HandleCompleteBacklogReview handles the CompleteBacklogReview RPC.
func (s *FleetCommandService) HandleCompleteBacklogReview(ctx context.Context, req *CompleteBacklogReviewRequest) (*CompleteBacklogReviewResponse, error) {
	clientID := interceptors.ClientIDFromContext(ctx)

	result, err := s.completeBacklogReview.Handle(ctx, command.CompleteBacklogReviewCmd{
		RequestID:   req.CeremonyID,
		CeremonyID:  req.CeremonyID,
		RequestedBy: clientID,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "complete backlog review: %v", err)
	}

	return &CompleteBacklogReviewResponse{
		Ceremony: backlogReviewResultToWire(result),
		Success:  true,
		Message:  "backlog review completed",
	}, nil
}

// HandleCancelBacklogReview handles the CancelBacklogReview RPC.
func (s *FleetCommandService) HandleCancelBacklogReview(ctx context.Context, req *CancelBacklogReviewRequest) (*CancelBacklogReviewResponse, error) {
	clientID := interceptors.ClientIDFromContext(ctx)

	result, err := s.cancelBacklogReview.Handle(ctx, command.CancelBacklogReviewCmd{
		RequestID:   req.CeremonyID,
		CeremonyID:  req.CeremonyID,
		RequestedBy: clientID,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "cancel backlog review: %v", err)
	}

	return &CancelBacklogReviewResponse{
		Ceremony: backlogReviewResultToWire(result),
		Success:  true,
		Message:  "backlog review cancelled",
	}, nil
}

// HandleApproveDecision handles the ApproveDecision RPC.
func (s *FleetCommandService) HandleApproveDecision(ctx context.Context, req *ApproveDecisionRequest) (*ApproveDecisionResponse, error) {
	clientID := interceptors.ClientIDFromContext(ctx)

	err := s.approveDecision.Handle(ctx, command.ApproveDecisionCmd{
		StoryID:     req.StoryID,
		DecisionID:  req.DecisionID,
		Comment:     req.Comment,
		RequestedBy: clientID,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "approve decision: %v", err)
	}

	return &ApproveDecisionResponse{
		Success: true,
		Message: "decision approved",
	}, nil
}

// HandleRejectDecision handles the RejectDecision RPC.
func (s *FleetCommandService) HandleRejectDecision(ctx context.Context, req *RejectDecisionRequest) (*RejectDecisionResponse, error) {
	clientID := interceptors.ClientIDFromContext(ctx)

	err := s.rejectDecision.Handle(ctx, command.RejectDecisionCmd{
		StoryID:     req.StoryID,
		DecisionID:  req.DecisionID,
		Reason:      req.Reason,
		RequestedBy: clientID,
	})
	if err != nil {
		return nil, status.Errorf(codes.Internal, "reject decision: %v", err)
	}

	return &RejectDecisionResponse{
		Success: true,
		Message: "decision rejected",
	}, nil
}

// ---------------------------------------------------------------------------
// Backlog review wire conversion helpers
// ---------------------------------------------------------------------------

func backlogReviewResultToWire(r ports.BacklogReviewResult) *BacklogReviewMsgWire {
	results := make([]*StoryReviewResultMsgWire, len(r.ReviewResults))
	for i, sr := range r.ReviewResults {
		results[i] = storyReviewResultToWire(sr)
	}
	return &BacklogReviewMsgWire{
		CeremonyID:    r.CeremonyID,
		StoryIDs:      r.StoryIDs,
		Status:        r.Status,
		ReviewResults: results,
		CreatedBy:     r.CreatedBy,
		CreatedAt:     r.CreatedAt,
		UpdatedAt:     r.UpdatedAt,
		StartedAt:     r.StartedAt,
		CompletedAt:   r.CompletedAt,
	}
}

func storyReviewResultToWire(sr ports.StoryReviewResultItem) *StoryReviewResultMsgWire {
	return &StoryReviewResultMsgWire{
		StoryID:            sr.StoryID,
		PlanPreliminary:    planPreliminaryToWire(sr.PlanPreliminary),
		ArchitectFeedback:  sr.ArchitectFeedback,
		QAFeedback:         sr.QAFeedback,
		DevopsFeedback:     sr.DevopsFeedback,
		Recommendations:    sr.Recommendations,
		ApprovalStatus:     sr.ApprovalStatus,
		ReviewedAt:         sr.ReviewedAt,
		ApprovedBy:         sr.ApprovedBy,
		ApprovedAt:         sr.ApprovedAt,
		RejectedBy:         sr.RejectedBy,
		RejectedAt:         sr.RejectedAt,
		RejectionReason:    sr.RejectionReason,
		PONotes:            sr.PONotes,
		POConcerns:         sr.POConcerns,
		PriorityAdjustment: sr.PriorityAdjustment,
		POPriorityReason:   sr.POPriorityReason,
		PlanID:             sr.PlanID,
	}
}

func planPreliminaryToWire(p ports.PlanPreliminaryResult) *PlanPreliminaryMsgWire {
	return &PlanPreliminaryMsgWire{
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

// ---------------------------------------------------------------------------
// gRPC service registration
// ---------------------------------------------------------------------------

// RegisterFleetCommandService registers the FleetCommandService with the gRPC
// server using a manually constructed ServiceDesc. The request/response types
// implement the legacy proto.Message interface so the default gRPC proto codec
// can marshal/unmarshal them via reflection-based protobuf encoding.
func RegisterFleetCommandService(gs *grpc.Server, svc *FleetCommandService) {
	gs.RegisterService(&fleetCommandServiceDesc, svc)
}

// fleetCommandServer is the interface required by gRPC's ServiceDesc.HandlerType.
type fleetCommandServer interface{}

// fleetCommandServiceDesc is the grpc.ServiceDesc for the FleetCommandService.
var fleetCommandServiceDesc = grpc.ServiceDesc{
	ServiceName: "fleet.proxy.v1.FleetCommandService",
	HandlerType: (*fleetCommandServer)(nil),
	Methods: []grpc.MethodDesc{
		{MethodName: "CreateProject", Handler: cmdCreateProjectHandler},
		{MethodName: "CreateEpic", Handler: cmdCreateEpicHandler},
		{MethodName: "CreateStory", Handler: cmdCreateStoryHandler},
		{MethodName: "TransitionStory", Handler: cmdTransitionStoryHandler},
		{MethodName: "CreateTask", Handler: cmdCreateTaskHandler},
		{MethodName: "StartPlanningCeremony", Handler: cmdStartPlanningCeremonyHandler},
		{MethodName: "StartBacklogReview", Handler: cmdStartBacklogReviewHandler},
		{MethodName: "CreateBacklogReview", Handler: cmdCreateBacklogReviewHandler},
		{MethodName: "ApproveReviewPlan", Handler: cmdApproveReviewPlanHandler},
		{MethodName: "RejectReviewPlan", Handler: cmdRejectReviewPlanHandler},
		{MethodName: "CompleteBacklogReview", Handler: cmdCompleteBacklogReviewHandler},
		{MethodName: "CancelBacklogReview", Handler: cmdCancelBacklogReviewHandler},
		{MethodName: "ApproveDecision", Handler: cmdApproveDecisionHandler},
		{MethodName: "RejectDecision", Handler: cmdRejectDecisionHandler},
	},
	Streams:  []grpc.StreamDesc{},
	Metadata: "fleet/proxy/v1/fleet_proxy.proto",
}

// ---------------------------------------------------------------------------
// gRPC adapter functions (generic signature -> typed handler)
// ---------------------------------------------------------------------------

func cmdCreateProjectHandler(srv any, ctx context.Context, dec func(any) error, interceptor grpc.UnaryServerInterceptor) (any, error) {
	req := new(CreateProjectRequest)
	if err := dec(req); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(*FleetCommandService).HandleCreateProject(ctx, req)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/fleet.proxy.v1.FleetCommandService/CreateProject"}
	return interceptor(ctx, req, info, func(ctx context.Context, r any) (any, error) {
		return srv.(*FleetCommandService).HandleCreateProject(ctx, r.(*CreateProjectRequest))
	})
}

func cmdCreateEpicHandler(srv any, ctx context.Context, dec func(any) error, interceptor grpc.UnaryServerInterceptor) (any, error) {
	req := new(CreateEpicRequest)
	if err := dec(req); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(*FleetCommandService).HandleCreateEpic(ctx, req)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/fleet.proxy.v1.FleetCommandService/CreateEpic"}
	return interceptor(ctx, req, info, func(ctx context.Context, r any) (any, error) {
		return srv.(*FleetCommandService).HandleCreateEpic(ctx, r.(*CreateEpicRequest))
	})
}

func cmdCreateStoryHandler(srv any, ctx context.Context, dec func(any) error, interceptor grpc.UnaryServerInterceptor) (any, error) {
	req := new(CreateStoryRequest)
	if err := dec(req); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(*FleetCommandService).HandleCreateStory(ctx, req)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/fleet.proxy.v1.FleetCommandService/CreateStory"}
	return interceptor(ctx, req, info, func(ctx context.Context, r any) (any, error) {
		return srv.(*FleetCommandService).HandleCreateStory(ctx, r.(*CreateStoryRequest))
	})
}

func cmdTransitionStoryHandler(srv any, ctx context.Context, dec func(any) error, interceptor grpc.UnaryServerInterceptor) (any, error) {
	req := new(TransitionStoryRequest)
	if err := dec(req); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(*FleetCommandService).HandleTransitionStory(ctx, req)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/fleet.proxy.v1.FleetCommandService/TransitionStory"}
	return interceptor(ctx, req, info, func(ctx context.Context, r any) (any, error) {
		return srv.(*FleetCommandService).HandleTransitionStory(ctx, r.(*TransitionStoryRequest))
	})
}

func cmdCreateTaskHandler(srv any, ctx context.Context, dec func(any) error, interceptor grpc.UnaryServerInterceptor) (any, error) {
	req := new(CreateTaskRequest)
	if err := dec(req); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(*FleetCommandService).HandleCreateTask(ctx, req)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/fleet.proxy.v1.FleetCommandService/CreateTask"}
	return interceptor(ctx, req, info, func(ctx context.Context, r any) (any, error) {
		return srv.(*FleetCommandService).HandleCreateTask(ctx, r.(*CreateTaskRequest))
	})
}

func cmdStartPlanningCeremonyHandler(srv any, ctx context.Context, dec func(any) error, interceptor grpc.UnaryServerInterceptor) (any, error) {
	req := new(StartPlanningCeremonyRequest)
	if err := dec(req); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(*FleetCommandService).HandleStartPlanningCeremony(ctx, req)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/fleet.proxy.v1.FleetCommandService/StartPlanningCeremony"}
	return interceptor(ctx, req, info, func(ctx context.Context, r any) (any, error) {
		return srv.(*FleetCommandService).HandleStartPlanningCeremony(ctx, r.(*StartPlanningCeremonyRequest))
	})
}

func cmdStartBacklogReviewHandler(srv any, ctx context.Context, dec func(any) error, interceptor grpc.UnaryServerInterceptor) (any, error) {
	req := new(StartBacklogReviewRequest)
	if err := dec(req); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(*FleetCommandService).HandleStartBacklogReview(ctx, req)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/fleet.proxy.v1.FleetCommandService/StartBacklogReview"}
	return interceptor(ctx, req, info, func(ctx context.Context, r any) (any, error) {
		return srv.(*FleetCommandService).HandleStartBacklogReview(ctx, r.(*StartBacklogReviewRequest))
	})
}

func cmdApproveDecisionHandler(srv any, ctx context.Context, dec func(any) error, interceptor grpc.UnaryServerInterceptor) (any, error) {
	req := new(ApproveDecisionRequest)
	if err := dec(req); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(*FleetCommandService).HandleApproveDecision(ctx, req)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/fleet.proxy.v1.FleetCommandService/ApproveDecision"}
	return interceptor(ctx, req, info, func(ctx context.Context, r any) (any, error) {
		return srv.(*FleetCommandService).HandleApproveDecision(ctx, r.(*ApproveDecisionRequest))
	})
}

func cmdRejectDecisionHandler(srv any, ctx context.Context, dec func(any) error, interceptor grpc.UnaryServerInterceptor) (any, error) {
	req := new(RejectDecisionRequest)
	if err := dec(req); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(*FleetCommandService).HandleRejectDecision(ctx, req)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/fleet.proxy.v1.FleetCommandService/RejectDecision"}
	return interceptor(ctx, req, info, func(ctx context.Context, r any) (any, error) {
		return srv.(*FleetCommandService).HandleRejectDecision(ctx, r.(*RejectDecisionRequest))
	})
}

func cmdCreateBacklogReviewHandler(srv any, ctx context.Context, dec func(any) error, interceptor grpc.UnaryServerInterceptor) (any, error) {
	req := new(CreateBacklogReviewRequest)
	if err := dec(req); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(*FleetCommandService).HandleCreateBacklogReview(ctx, req)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/fleet.proxy.v1.FleetCommandService/CreateBacklogReview"}
	return interceptor(ctx, req, info, func(ctx context.Context, r any) (any, error) {
		return srv.(*FleetCommandService).HandleCreateBacklogReview(ctx, r.(*CreateBacklogReviewRequest))
	})
}

func cmdApproveReviewPlanHandler(srv any, ctx context.Context, dec func(any) error, interceptor grpc.UnaryServerInterceptor) (any, error) {
	req := new(ApproveReviewPlanProxyRequest)
	if err := dec(req); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(*FleetCommandService).HandleApproveReviewPlan(ctx, req)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/fleet.proxy.v1.FleetCommandService/ApproveReviewPlan"}
	return interceptor(ctx, req, info, func(ctx context.Context, r any) (any, error) {
		return srv.(*FleetCommandService).HandleApproveReviewPlan(ctx, r.(*ApproveReviewPlanProxyRequest))
	})
}

func cmdRejectReviewPlanHandler(srv any, ctx context.Context, dec func(any) error, interceptor grpc.UnaryServerInterceptor) (any, error) {
	req := new(RejectReviewPlanProxyRequest)
	if err := dec(req); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(*FleetCommandService).HandleRejectReviewPlan(ctx, req)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/fleet.proxy.v1.FleetCommandService/RejectReviewPlan"}
	return interceptor(ctx, req, info, func(ctx context.Context, r any) (any, error) {
		return srv.(*FleetCommandService).HandleRejectReviewPlan(ctx, r.(*RejectReviewPlanProxyRequest))
	})
}

func cmdCompleteBacklogReviewHandler(srv any, ctx context.Context, dec func(any) error, interceptor grpc.UnaryServerInterceptor) (any, error) {
	req := new(CompleteBacklogReviewRequest)
	if err := dec(req); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(*FleetCommandService).HandleCompleteBacklogReview(ctx, req)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/fleet.proxy.v1.FleetCommandService/CompleteBacklogReview"}
	return interceptor(ctx, req, info, func(ctx context.Context, r any) (any, error) {
		return srv.(*FleetCommandService).HandleCompleteBacklogReview(ctx, r.(*CompleteBacklogReviewRequest))
	})
}

func cmdCancelBacklogReviewHandler(srv any, ctx context.Context, dec func(any) error, interceptor grpc.UnaryServerInterceptor) (any, error) {
	req := new(CancelBacklogReviewRequest)
	if err := dec(req); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(*FleetCommandService).HandleCancelBacklogReview(ctx, req)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/fleet.proxy.v1.FleetCommandService/CancelBacklogReview"}
	return interceptor(ctx, req, info, func(ctx context.Context, r any) (any, error) {
		return srv.(*FleetCommandService).HandleCancelBacklogReview(ctx, r.(*CancelBacklogReviewRequest))
	})
}
