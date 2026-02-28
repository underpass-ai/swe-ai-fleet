package domain

// EpicSummary is a read-model representing an epic as returned by the
// fleet control plane. It is intentionally flat and uses strings for
// timestamps so the domain stays free of serialisation concerns.
type EpicSummary struct {
	ID          string
	ProjectID   string
	Title       string
	Description string
	Status      string
	CreatedAt   string
	UpdatedAt   string
}
