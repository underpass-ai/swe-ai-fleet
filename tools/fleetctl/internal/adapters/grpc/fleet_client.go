package grpc

import (
	"context"
	"fmt"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// FleetClient implements ports.FleetClient over gRPC. Method bodies are
// stubs until the proto-generated client stubs are available.
type FleetClient struct {
	conn *Connection
}

// NewFleetClient creates a FleetClient bound to the given Connection.
func NewFleetClient(conn *Connection) *FleetClient {
	return &FleetClient{conn: conn}
}

// Enroll registers this device with the control plane using an API key
// and a CSR. Uses a hand-crafted gRPC call matching the proto wire format.
func (c *FleetClient) Enroll(ctx context.Context, apiKey, deviceID string, csrPEM []byte) (certPEM, caPEM []byte, clientID, expiresAt string, err error) {
	req := &EnrollRequest{
		APIKey:        apiKey,
		CSRPEM:        csrPEM,
		DeviceID:      deviceID,
		ClientVersion: "dev",
	}
	resp := &EnrollResponse{}
	err = c.conn.Conn().Invoke(ctx, "/fleet.proxy.v1.EnrollmentService/Enroll", req, resp)
	if err != nil {
		return nil, nil, "", "", fmt.Errorf("enroll RPC: %w", err)
	}
	return resp.ClientCertPEM, resp.CAChainPEM, resp.ClientID, resp.ExpiresAt, nil
}

// Renew requests a new certificate using the existing mTLS identity.
func (c *FleetClient) Renew(ctx context.Context, csrPEM []byte) (certPEM, caPEM []byte, expiresAt string, err error) {
	return nil, nil, "", fmt.Errorf("not implemented: awaiting proto generation")
}

// CreateProject creates a new project in the control plane.
func (c *FleetClient) CreateProject(ctx context.Context, requestID, name, description string) (domain.ProjectSummary, error) {
	return domain.ProjectSummary{}, fmt.Errorf("not implemented: awaiting proto generation")
}

// CreateStory creates a new story under the given epic.
func (c *FleetClient) CreateStory(ctx context.Context, requestID, epicID, title, brief string) (domain.StorySummary, error) {
	return domain.StorySummary{}, fmt.Errorf("not implemented: awaiting proto generation")
}

// TransitionStory moves a story to the specified target state.
func (c *FleetClient) TransitionStory(ctx context.Context, storyID, targetState string) error {
	return fmt.Errorf("not implemented: awaiting proto generation")
}

// StartCeremony kicks off a ceremony instance for the given story.
func (c *FleetClient) StartCeremony(ctx context.Context, requestID, ceremonyID, definitionName, storyID string, stepIDs []string) (domain.CeremonyStatus, error) {
	return domain.CeremonyStatus{}, fmt.Errorf("not implemented: awaiting proto generation")
}

// ListProjects returns all projects visible to the authenticated identity.
func (c *FleetClient) ListProjects(ctx context.Context) ([]domain.ProjectSummary, error) {
	return nil, fmt.Errorf("not implemented: awaiting proto generation")
}

// ListStories returns stories with optional filtering and pagination.
func (c *FleetClient) ListStories(ctx context.Context, epicID, stateFilter string, limit, offset int32) ([]domain.StorySummary, int32, error) {
	return nil, 0, fmt.Errorf("not implemented: awaiting proto generation")
}

// ListTasks returns tasks with optional filtering and pagination.
func (c *FleetClient) ListTasks(ctx context.Context, storyID, statusFilter string, limit, offset int32) ([]domain.TaskSummary, int32, error) {
	return nil, 0, fmt.Errorf("not implemented: awaiting proto generation")
}

// ListCeremonies returns ceremony instances with optional filtering and pagination.
func (c *FleetClient) ListCeremonies(ctx context.Context, ceremonyID, statusFilter string, limit, offset int32) ([]domain.CeremonyStatus, int32, error) {
	return nil, 0, fmt.Errorf("not implemented: awaiting proto generation")
}

// GetCeremony returns the current status of a ceremony instance.
func (c *FleetClient) GetCeremony(ctx context.Context, instanceID string) (domain.CeremonyStatus, error) {
	return domain.CeremonyStatus{}, fmt.Errorf("not implemented: awaiting proto generation")
}

// ApproveDecision approves a pending decision for the given story.
func (c *FleetClient) ApproveDecision(ctx context.Context, storyID, decisionID, comment string) error {
	return fmt.Errorf("not implemented: awaiting proto generation")
}

// RejectDecision rejects a pending decision for the given story.
func (c *FleetClient) RejectDecision(ctx context.Context, storyID, decisionID, reason string) error {
	return fmt.Errorf("not implemented: awaiting proto generation")
}

// Close releases the underlying gRPC connection.
func (c *FleetClient) Close() error {
	return c.conn.Close()
}
