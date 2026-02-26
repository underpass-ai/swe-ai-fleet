package query

import (
	"context"
	"errors"
	"fmt"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// GetCeremonyQuery carries the identifier for fetching a ceremony instance.
type GetCeremonyQuery struct {
	InstanceID string
}

// GetCeremonyHandler retrieves the current status of a ceremony instance
// from the fleet control plane.
type GetCeremonyHandler struct {
	client ports.FleetClient
}

// NewGetCeremonyHandler returns a handler wired to the given FleetClient.
func NewGetCeremonyHandler(client ports.FleetClient) *GetCeremonyHandler {
	return &GetCeremonyHandler{client: client}
}

// Handle fetches the ceremony status for the given instance ID.
func (h *GetCeremonyHandler) Handle(ctx context.Context, q GetCeremonyQuery) (domain.CeremonyStatus, error) {
	if q.InstanceID == "" {
		return domain.CeremonyStatus{}, errors.New("get_ceremony: instance_id is required")
	}

	status, err := h.client.GetCeremony(ctx, q.InstanceID)
	if err != nil {
		return domain.CeremonyStatus{}, fmt.Errorf("get_ceremony: %w", err)
	}
	return status, nil
}
