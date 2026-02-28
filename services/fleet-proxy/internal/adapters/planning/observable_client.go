package planning

import (
	"context"
	"crypto/rand"
	"encoding/json"
	"fmt"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/event"
)

// ObservableClient wraps a PlanningClient and publishes rpc.outbound events
// for every outbound gRPC call to the planning service.
type ObservableClient struct {
	inner     ports.PlanningClient
	publisher ports.EventPublisher
}

// NewObservableClient creates a decorator that records outbound RPC trace events.
func NewObservableClient(inner ports.PlanningClient, pub ports.EventPublisher) *ObservableClient {
	return &ObservableClient{inner: inner, publisher: pub}
}

// marshalAny serialises an arbitrary value to JSON for inclusion in event payloads.
// Returns nil on failure so the event is still published without the body.
func marshalAny(v any) json.RawMessage {
	if v == nil {
		return nil
	}
	data, err := json.Marshal(v)
	if err != nil {
		return nil
	}
	return data
}

func (o *ObservableClient) publish(method string, request, response any, err error, dur time.Duration) {
	type payload struct {
		Method     string          `json:"method"`
		Success    bool            `json:"success"`
		Error      string          `json:"error,omitempty"`
		DurationMs int64           `json:"duration_ms"`
		Request    json.RawMessage `json:"request,omitempty"`
		Response   json.RawMessage `json:"response,omitempty"`
	}
	p := payload{
		Method:     method,
		Success:    err == nil,
		DurationMs: dur.Milliseconds(),
		Request:    marshalAny(request),
		Response:   marshalAny(response),
	}
	if err != nil {
		p.Error = err.Error()
	}
	data, _ := json.Marshal(p)

	var b [16]byte
	_, _ = rand.Read(b[:])

	o.publisher.Publish(event.FleetEvent{
		Type:           event.EventRPCOutbound,
		IdempotencyKey: fmt.Sprintf("%x", b),
		CorrelationID:  method,
		Timestamp:      time.Now(),
		Producer:       "fleet-proxy",
		Payload:        data,
	})
}

func (o *ObservableClient) CreateProject(ctx context.Context, name, description, createdBy string) (string, error) {
	start := time.Now()
	id, err := o.inner.CreateProject(ctx, name, description, createdBy)
	o.publish("CreateProject",
		map[string]string{"name": name, "description": description, "created_by": createdBy},
		map[string]string{"id": id}, err, time.Since(start))
	return id, err
}

func (o *ObservableClient) CreateEpic(ctx context.Context, projectID, title, description string) (string, error) {
	start := time.Now()
	id, err := o.inner.CreateEpic(ctx, projectID, title, description)
	o.publish("CreateEpic",
		map[string]string{"project_id": projectID, "title": title, "description": description},
		map[string]string{"id": id}, err, time.Since(start))
	return id, err
}

func (o *ObservableClient) CreateStory(ctx context.Context, epicID, title, brief, createdBy string) (string, error) {
	start := time.Now()
	id, err := o.inner.CreateStory(ctx, epicID, title, brief, createdBy)
	o.publish("CreateStory",
		map[string]string{"epic_id": epicID, "title": title, "brief": brief, "created_by": createdBy},
		map[string]string{"id": id}, err, time.Since(start))
	return id, err
}

func (o *ObservableClient) TransitionStory(ctx context.Context, storyID, targetState string) error {
	start := time.Now()
	err := o.inner.TransitionStory(ctx, storyID, targetState)
	o.publish("TransitionStory",
		map[string]string{"story_id": storyID, "target_state": targetState},
		nil, err, time.Since(start))
	return err
}

func (o *ObservableClient) CreateTask(ctx context.Context, storyID, title, description, taskType, assignedTo string, estimatedHours, priority int32) (string, error) {
	start := time.Now()
	id, err := o.inner.CreateTask(ctx, storyID, title, description, taskType, assignedTo, estimatedHours, priority)
	o.publish("CreateTask",
		map[string]any{"story_id": storyID, "title": title, "description": description, "task_type": taskType, "assigned_to": assignedTo, "estimated_hours": estimatedHours, "priority": priority},
		map[string]string{"id": id}, err, time.Since(start))
	return id, err
}

func (o *ObservableClient) ApproveDecision(ctx context.Context, storyID, decisionID, comment string) error {
	start := time.Now()
	err := o.inner.ApproveDecision(ctx, storyID, decisionID, comment)
	o.publish("ApproveDecision",
		map[string]string{"story_id": storyID, "decision_id": decisionID, "comment": comment},
		nil, err, time.Since(start))
	return err
}

func (o *ObservableClient) RejectDecision(ctx context.Context, storyID, decisionID, reason string) error {
	start := time.Now()
	err := o.inner.RejectDecision(ctx, storyID, decisionID, reason)
	o.publish("RejectDecision",
		map[string]string{"story_id": storyID, "decision_id": decisionID, "reason": reason},
		nil, err, time.Since(start))
	return err
}

func (o *ObservableClient) ListProjects(ctx context.Context, statusFilter string, limit, offset int32) ([]ports.ProjectResult, int32, error) {
	start := time.Now()
	res, total, err := o.inner.ListProjects(ctx, statusFilter, limit, offset)
	o.publish("ListProjects",
		map[string]any{"status_filter": statusFilter, "limit": limit, "offset": offset},
		map[string]any{"total": total, "count": len(res), "projects": res}, err, time.Since(start))
	return res, total, err
}

func (o *ObservableClient) ListEpics(ctx context.Context, projectID, statusFilter string, limit, offset int32) ([]ports.EpicResult, int32, error) {
	start := time.Now()
	res, total, err := o.inner.ListEpics(ctx, projectID, statusFilter, limit, offset)
	o.publish("ListEpics",
		map[string]any{"project_id": projectID, "status_filter": statusFilter, "limit": limit, "offset": offset},
		map[string]any{"total": total, "count": len(res), "epics": res}, err, time.Since(start))
	return res, total, err
}

func (o *ObservableClient) ListStories(ctx context.Context, epicID, stateFilter string, limit, offset int32) ([]ports.StoryResult, int32, error) {
	start := time.Now()
	res, total, err := o.inner.ListStories(ctx, epicID, stateFilter, limit, offset)
	o.publish("ListStories",
		map[string]any{"epic_id": epicID, "state_filter": stateFilter, "limit": limit, "offset": offset},
		map[string]any{"total": total, "count": len(res), "stories": res}, err, time.Since(start))
	return res, total, err
}

func (o *ObservableClient) ListTasks(ctx context.Context, storyID, statusFilter string, limit, offset int32) ([]ports.TaskResult, int32, error) {
	start := time.Now()
	res, total, err := o.inner.ListTasks(ctx, storyID, statusFilter, limit, offset)
	o.publish("ListTasks",
		map[string]any{"story_id": storyID, "status_filter": statusFilter, "limit": limit, "offset": offset},
		map[string]any{"total": total, "count": len(res), "tasks": res}, err, time.Since(start))
	return res, total, err
}

func (o *ObservableClient) CreateBacklogReview(ctx context.Context, createdBy string, storyIDs []string) (ports.BacklogReviewResult, error) {
	start := time.Now()
	res, err := o.inner.CreateBacklogReview(ctx, createdBy, storyIDs)
	o.publish("CreateBacklogReview",
		map[string]any{"created_by": createdBy, "story_ids": storyIDs},
		res, err, time.Since(start))
	return res, err
}

func (o *ObservableClient) StartBacklogReview(ctx context.Context, ceremonyID, startedBy string) (ports.BacklogReviewResult, int32, error) {
	start := time.Now()
	res, total, err := o.inner.StartBacklogReview(ctx, ceremonyID, startedBy)
	o.publish("StartBacklogReview",
		map[string]string{"ceremony_id": ceremonyID, "started_by": startedBy},
		map[string]any{"review": res, "total": total}, err, time.Since(start))
	return res, total, err
}

func (o *ObservableClient) GetBacklogReview(ctx context.Context, ceremonyID string) (ports.BacklogReviewResult, error) {
	start := time.Now()
	res, err := o.inner.GetBacklogReview(ctx, ceremonyID)
	o.publish("GetBacklogReview",
		map[string]string{"ceremony_id": ceremonyID},
		res, err, time.Since(start))
	return res, err
}

func (o *ObservableClient) ListBacklogReviews(ctx context.Context, statusFilter string, limit, offset int32) ([]ports.BacklogReviewResult, int32, error) {
	start := time.Now()
	res, total, err := o.inner.ListBacklogReviews(ctx, statusFilter, limit, offset)
	o.publish("ListBacklogReviews",
		map[string]any{"status_filter": statusFilter, "limit": limit, "offset": offset},
		map[string]any{"total": total, "count": len(res), "reviews": res}, err, time.Since(start))
	return res, total, err
}

func (o *ObservableClient) ApproveReviewPlan(ctx context.Context, ceremonyID, storyID, approvedBy, poNotes, poConcerns, priorityAdj, prioReason string) (ports.BacklogReviewResult, string, error) {
	start := time.Now()
	res, planID, err := o.inner.ApproveReviewPlan(ctx, ceremonyID, storyID, approvedBy, poNotes, poConcerns, priorityAdj, prioReason)
	o.publish("ApproveReviewPlan",
		map[string]string{"ceremony_id": ceremonyID, "story_id": storyID, "approved_by": approvedBy, "po_notes": poNotes, "po_concerns": poConcerns, "priority_adj": priorityAdj, "prio_reason": prioReason},
		map[string]any{"review": res, "plan_id": planID}, err, time.Since(start))
	return res, planID, err
}

func (o *ObservableClient) RejectReviewPlan(ctx context.Context, ceremonyID, storyID, rejectedBy, reason string) (ports.BacklogReviewResult, error) {
	start := time.Now()
	res, err := o.inner.RejectReviewPlan(ctx, ceremonyID, storyID, rejectedBy, reason)
	o.publish("RejectReviewPlan",
		map[string]string{"ceremony_id": ceremonyID, "story_id": storyID, "rejected_by": rejectedBy, "reason": reason},
		res, err, time.Since(start))
	return res, err
}

func (o *ObservableClient) CompleteBacklogReview(ctx context.Context, ceremonyID, completedBy string) (ports.BacklogReviewResult, error) {
	start := time.Now()
	res, err := o.inner.CompleteBacklogReview(ctx, ceremonyID, completedBy)
	o.publish("CompleteBacklogReview",
		map[string]string{"ceremony_id": ceremonyID, "completed_by": completedBy},
		res, err, time.Since(start))
	return res, err
}

func (o *ObservableClient) CancelBacklogReview(ctx context.Context, ceremonyID, cancelledBy string) (ports.BacklogReviewResult, error) {
	start := time.Now()
	res, err := o.inner.CancelBacklogReview(ctx, ceremonyID, cancelledBy)
	o.publish("CancelBacklogReview",
		map[string]string{"ceremony_id": ceremonyID, "cancelled_by": cancelledBy},
		res, err, time.Since(start))
	return res, err
}
