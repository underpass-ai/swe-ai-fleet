package query

import (
	"context"
	"errors"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

// GetCeremonyQuery carries the parameters for fetching a single ceremony instance.
type GetCeremonyQuery struct {
	InstanceID string
}

// GetCeremonyHandler handles ceremony fetch queries.
type GetCeremonyHandler struct {
	ceremony ports.CeremonyClient
}

// NewGetCeremonyHandler wires the handler to the ceremony port.
func NewGetCeremonyHandler(c ports.CeremonyClient) *GetCeremonyHandler {
	return &GetCeremonyHandler{ceremony: c}
}

// Handle validates the query and delegates to the ceremony port.
func (h *GetCeremonyHandler) Handle(ctx context.Context, q GetCeremonyQuery) (ports.CeremonyResult, error) {
	if q.InstanceID == "" {
		return ports.CeremonyResult{}, errors.New("instance ID is required")
	}

	return h.ceremony.GetCeremony(ctx, q.InstanceID)
}
