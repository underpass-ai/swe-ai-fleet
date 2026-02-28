package domain

// BacklogReview represents a backlog review ceremony as returned by the
// fleet control plane.
type BacklogReview struct {
	CeremonyID    string
	Status        string
	CreatedBy     string
	CreatedAt     string
	UpdatedAt     string
	StartedAt     string
	CompletedAt   string
	StoryIDs      []string
	ReviewResults []StoryReviewResult
}

// StoryReviewResult holds the multi-council review result for a single story.
type StoryReviewResult struct {
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
	PlanPreliminary    PlanPreliminary
}

// PlanPreliminary holds the preliminary plan generated during backlog review.
type PlanPreliminary struct {
	Title               string
	Description         string
	TechnicalNotes      string
	EstimatedComplexity string
	AcceptanceCriteria  []string
	Roles               []string
	Dependencies        []string
	TasksOutline        []string
}
