package domain

// TaskSummary is a read-model representing a task as returned by the
// fleet control plane.
type TaskSummary struct {
	ID             string
	StoryID        string
	Title          string
	Description    string
	Type           string
	Status         string
	AssignedTo     string
	EstimatedHours int32
	Priority       int32
	CreatedAt      string
	UpdatedAt      string
}
