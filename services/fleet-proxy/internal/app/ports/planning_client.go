// Package ports defines the driven-side interfaces (secondary ports) for the
// fleet-proxy application layer. Adapters implement these interfaces to connect
// to external systems (planning gRPC service, ceremony processor, NATS, PKI, etc.).
//
// All interfaces are expressed in terms of basic Go types and domain value objects
// to avoid circular imports with the command/query packages.
package ports

import "context"

// PlanningClient is a port for communicating with the upstream planning service.
// It abstracts gRPC or any other transport behind a domain-oriented interface.
type PlanningClient interface {
	// CreateProject creates a new project and returns its ID.
	CreateProject(ctx context.Context, name, description, createdBy string) (projectID string, err error)

	// CreateEpic creates a new epic under a project and returns its ID.
	CreateEpic(ctx context.Context, projectID, title, description string) (epicID string, err error)

	// CreateStory creates a new story under an epic and returns its ID.
	CreateStory(ctx context.Context, epicID, title, brief, createdBy string) (storyID string, err error)

	// TransitionStory moves a story to a new state.
	TransitionStory(ctx context.Context, storyID, targetState string) error

	// CreateTask creates a new task under a story and returns its ID.
	CreateTask(ctx context.Context, storyID, title, description, taskType, assignedTo string, estimatedHours, priority int32) (taskID string, err error)

	// ApproveDecision approves a pending decision on a story.
	ApproveDecision(ctx context.Context, storyID, decisionID, comment string) error

	// RejectDecision rejects a pending decision on a story.
	RejectDecision(ctx context.Context, storyID, decisionID, reason string) error

	// ListProjects returns a page of projects matching the filter.
	ListProjects(ctx context.Context, statusFilter string, limit, offset int32) ([]ProjectResult, int32, error)

	// ListEpics returns a page of epics for a project matching the filter.
	ListEpics(ctx context.Context, projectID, statusFilter string, limit, offset int32) ([]EpicResult, int32, error)

	// ListStories returns a page of stories for an epic matching the filter.
	ListStories(ctx context.Context, epicID, stateFilter string, limit, offset int32) ([]StoryResult, int32, error)

	// ListTasks returns a page of tasks for a story matching the filter.
	ListTasks(ctx context.Context, storyID, statusFilter string, limit, offset int32) ([]TaskResult, int32, error)

	// CreateBacklogReview creates a new backlog review ceremony.
	CreateBacklogReview(ctx context.Context, createdBy string, storyIDs []string) (BacklogReviewResult, error)

	// StartBacklogReview starts a backlog review ceremony and triggers council deliberations.
	StartBacklogReview(ctx context.Context, ceremonyID, startedBy string) (BacklogReviewResult, int32, error)

	// GetBacklogReview fetches a single backlog review ceremony by ID.
	GetBacklogReview(ctx context.Context, ceremonyID string) (BacklogReviewResult, error)

	// ListBacklogReviews returns a page of backlog review ceremonies matching the filter.
	ListBacklogReviews(ctx context.Context, statusFilter string, limit, offset int32) ([]BacklogReviewResult, int32, error)

	// ApproveReviewPlan approves a story's review plan within a backlog review ceremony.
	ApproveReviewPlan(ctx context.Context, ceremonyID, storyID, approvedBy, poNotes, poConcerns, priorityAdj, prioReason string) (BacklogReviewResult, string, error)

	// RejectReviewPlan rejects a story's review plan within a backlog review ceremony.
	RejectReviewPlan(ctx context.Context, ceremonyID, storyID, rejectedBy, reason string) (BacklogReviewResult, error)

	// CompleteBacklogReview marks a backlog review ceremony as completed.
	CompleteBacklogReview(ctx context.Context, ceremonyID, completedBy string) (BacklogReviewResult, error)

	// CancelBacklogReview cancels a backlog review ceremony.
	CancelBacklogReview(ctx context.Context, ceremonyID, cancelledBy string) (BacklogReviewResult, error)
}

// ProjectResult holds the data returned when listing or fetching a project.
type ProjectResult struct {
	ProjectID   string
	Name        string
	Description string
	Status      string
	Owner       string
	CreatedAt   string
	UpdatedAt   string
}

// EpicResult holds the data returned when listing or fetching an epic.
type EpicResult struct {
	EpicID      string
	ProjectID   string
	Title       string
	Description string
	Status      string
	CreatedAt   string
	UpdatedAt   string
}

// StoryResult holds the data returned when listing or fetching a story.
type StoryResult struct {
	StoryID   string
	EpicID    string
	Title     string
	Brief     string
	State     string
	CreatedAt string
	UpdatedAt string
}

// TaskResult holds the data returned when listing or fetching a task.
type TaskResult struct {
	TaskID         string
	StoryID        string
	Title          string
	Description    string
	Type           string
	AssignedTo     string
	EstimatedHours int32
	Priority       int32
	Status         string
	CreatedAt      string
	UpdatedAt      string
}

// BacklogReviewResult holds the data returned when fetching a backlog review ceremony.
type BacklogReviewResult struct {
	CeremonyID    string
	Status        string
	CreatedBy     string
	CreatedAt     string
	UpdatedAt     string
	StartedAt     string
	CompletedAt   string
	StoryIDs      []string
	ReviewResults []StoryReviewResultItem
}

// StoryReviewResultItem holds the review result for a single story within a backlog review.
type StoryReviewResultItem struct {
	StoryID            string
	ArchitectFeedback  string
	QAFeedback         string
	DevopsFeedback     string
	ApprovalStatus     string
	ReviewedAt         string
	ApprovedBy         string
	ApprovedAt         string
	RejectedBy         string
	RejectedAt         string
	RejectionReason    string
	PONotes            string
	POConcerns         string
	PriorityAdjustment string
	POPriorityReason   string
	PlanID             string
	Recommendations    []string
	PlanPreliminary    PlanPreliminaryResult
}

// PlanPreliminaryResult holds the preliminary plan generated during backlog review.
type PlanPreliminaryResult struct {
	Title               string
	Description         string
	TechnicalNotes      string
	EstimatedComplexity string
	AcceptanceCriteria  []string
	Roles               []string
	Dependencies        []string
	TasksOutline        []string
}
