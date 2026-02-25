package ports

import "context"

// CeremonyClient is a port for communicating with the ceremony processor service.
type CeremonyClient interface {
	// StartCeremony starts a ceremony instance and returns the instance ID.
	StartCeremony(ctx context.Context, ceremonyID, definitionName, storyID string, stepIDs []string) (instanceID string, err error)

	// StartBacklogReview starts a backlog review ceremony and returns the review count.
	StartBacklogReview(ctx context.Context, ceremonyID string) (reviewCount int32, err error)

	// GetCeremony fetches a ceremony instance by its instance ID.
	GetCeremony(ctx context.Context, instanceID string) (CeremonyResult, error)

	// ListCeremonies returns a page of ceremonies matching the filter.
	ListCeremonies(ctx context.Context, ceremonyID, statusFilter string, limit, offset int32) ([]CeremonyResult, int32, error)
}

// CeremonyResult holds the data returned when fetching or listing a ceremony instance.
type CeremonyResult struct {
	InstanceID     string
	CeremonyID     string
	DefinitionName string
	StoryID        string
	Status         string
	StepStatuses   map[string]string
	CreatedAt      string
	UpdatedAt      string
}
