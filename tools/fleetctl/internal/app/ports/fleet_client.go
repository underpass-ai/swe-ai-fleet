package ports

import (
	"context"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

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

	// ListProjects returns all projects visible to the authenticated identity.
	ListProjects(ctx context.Context) ([]domain.ProjectSummary, error)

	// ListStories returns stories belonging to the given epic with optional
	// state filter and pagination. Returns the matching stories and total count.
	ListStories(ctx context.Context, epicID, stateFilter string, limit, offset int32) ([]domain.StorySummary, int32, error)

	// ListTasks returns tasks belonging to the given story with optional
	// status filter and pagination. Returns the matching tasks and total count.
	ListTasks(ctx context.Context, storyID, statusFilter string, limit, offset int32) ([]domain.TaskSummary, int32, error)

	// ListCeremonies returns ceremony instances matching the optional filters
	// with pagination. Returns the matching ceremonies and total count.
	ListCeremonies(ctx context.Context, ceremonyID, statusFilter string, limit, offset int32) ([]domain.CeremonyStatus, int32, error)

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

	// Close releases any underlying transport resources.
	Close() error
}
