package ports

import (
	"context"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// CreateTaskInput carries the parameters for creating a new task.
type CreateTaskInput struct {
	RequestID      string
	StoryID        string
	Title          string
	Description    string
	TaskType       string
	AssignedTo     string
	EstimatedHours int32
	Priority       int32
}

// ApproveReviewPlanInput carries the parameters for approving a story's review plan.
type ApproveReviewPlanInput struct {
	RequestID   string
	CeremonyID  string
	StoryID     string
	PONotes     string
	POConcerns  string
	PriorityAdj string
	PrioReason  string
}

// FleetClient abstracts communication with the fleet control plane.
// Implementations live in the adapters layer (gRPC, HTTP, mock, etc.).
type FleetClient interface {
	// Enroll registers this device with the control plane using an API key
	// and a CSR. It returns the signed certificate, CA chain, assigned
	// client ID, and expiration timestamp.
	Enroll(ctx context.Context, apiKey, deviceID string, csrPEM []byte) (certPEM, caPEM []byte, clientID, expiresAt string, err error)

	// Renew requests a new certificate using the existing mTLS identity.
	Renew(ctx context.Context, csrPEM []byte) (certPEM, caPEM []byte, expiresAt string, err error)

	// CreateProject creates a new project in the control plane.
	CreateProject(ctx context.Context, requestID, name, description string) (domain.ProjectSummary, error)

	// CreateStory creates a new story under the given epic.
	CreateStory(ctx context.Context, requestID, epicID, title, brief string) (domain.StorySummary, error)

	// TransitionStory moves a story to the specified target state.
	TransitionStory(ctx context.Context, storyID, targetState string) error

	// StartCeremony kicks off a ceremony instance for the given story.
	StartCeremony(ctx context.Context, requestID, ceremonyID, definitionName, storyID string, stepIDs []string) (domain.CeremonyStatus, error)

	// CreateEpic creates a new epic under the given project.
	CreateEpic(ctx context.Context, requestID, projectID, title, description string) (domain.EpicSummary, error)

	// ListProjects returns projects visible to the authenticated identity
	// with optional status filter and pagination. Returns the matching
	// projects and total count.
	ListProjects(ctx context.Context, statusFilter string, limit, offset int32) ([]domain.ProjectSummary, int32, error)

	// ListEpics returns epics belonging to the given project with optional
	// status filter and pagination. Returns the matching epics and total count.
	ListEpics(ctx context.Context, projectID, statusFilter string, limit, offset int32) ([]domain.EpicSummary, int32, error)

	// ListStories returns stories belonging to the given epic with optional
	// state filter and pagination. Returns the matching stories and total count.
	ListStories(ctx context.Context, epicID, stateFilter string, limit, offset int32) ([]domain.StorySummary, int32, error)

	// CreateTask creates a new task under the given story.
	CreateTask(ctx context.Context, req CreateTaskInput) (domain.TaskSummary, error)

	// ListTasks returns tasks belonging to the given story with optional
	// status filter and pagination. Returns the matching tasks and total count.
	ListTasks(ctx context.Context, storyID, statusFilter string, limit, offset int32) ([]domain.TaskSummary, int32, error)

	// ListCeremonies returns ceremony instances matching the optional filters
	// with pagination. storyID filters by story; statusFilter by state.
	ListCeremonies(ctx context.Context, storyID, statusFilter string, limit, offset int32) ([]domain.CeremonyStatus, int32, error)

	// GetCeremony returns the current status of a ceremony instance.
	GetCeremony(ctx context.Context, instanceID string) (domain.CeremonyStatus, error)

	// ApproveDecision approves a pending decision for the given story.
	ApproveDecision(ctx context.Context, storyID, decisionID, comment string) error

	// RejectDecision rejects a pending decision for the given story.
	RejectDecision(ctx context.Context, storyID, decisionID, reason string) error

	// WatchEvents opens a server-streaming subscription for fleet events.
	// The returned channel is closed when the context is cancelled or the
	// server terminates the stream.
	WatchEvents(ctx context.Context, eventTypes []string, projectID string) (<-chan domain.FleetEvent, error)

	// CreateBacklogReview creates a new backlog review ceremony.
	CreateBacklogReview(ctx context.Context, requestID string, storyIDs []string) (domain.BacklogReview, error)

	// StartBacklogReview starts a backlog review ceremony.
	StartBacklogReview(ctx context.Context, requestID, ceremonyID string) (domain.BacklogReview, int32, error)

	// GetBacklogReview fetches a single backlog review ceremony.
	GetBacklogReview(ctx context.Context, ceremonyID string) (domain.BacklogReview, error)

	// ListBacklogReviews returns backlog review ceremonies with filtering.
	ListBacklogReviews(ctx context.Context, statusFilter string, limit, offset int32) ([]domain.BacklogReview, int32, error)

	// ApproveReviewPlan approves a story's review plan.
	ApproveReviewPlan(ctx context.Context, req ApproveReviewPlanInput) (domain.BacklogReview, string, error)

	// RejectReviewPlan rejects a story's review plan.
	RejectReviewPlan(ctx context.Context, requestID, ceremonyID, storyID, reason string) (domain.BacklogReview, error)

	// CompleteBacklogReview marks a backlog review ceremony as completed.
	CompleteBacklogReview(ctx context.Context, requestID, ceremonyID string) (domain.BacklogReview, error)

	// CancelBacklogReview cancels a backlog review ceremony.
	CancelBacklogReview(ctx context.Context, requestID, ceremonyID string) (domain.BacklogReview, error)

	// Close releases any underlying transport resources.
	Close() error
}
