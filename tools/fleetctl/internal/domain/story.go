package domain

// StorySummary is a read-model representing a story as returned by the
// fleet control plane.
type StorySummary struct {
	ID        string
	EpicID    string
	Title     string
	Brief     string
	State     string
	DorScore  int32
	CreatedBy string
	CreatedAt string
	UpdatedAt string
}
