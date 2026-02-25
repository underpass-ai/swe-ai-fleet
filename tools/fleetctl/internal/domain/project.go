package domain

// ProjectSummary is a read-model representing a project as returned by the
// fleet control plane. It is intentionally flat and uses strings for
// timestamps so the domain stays free of serialisation concerns.
type ProjectSummary struct {
	ID          string
	Name        string
	Description string
	Status      string
	Owner       string
	CreatedAt   string
	UpdatedAt   string
}
