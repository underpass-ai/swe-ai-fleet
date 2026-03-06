package query

import (
	"context"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

// ListCeremoniesQuery carries the parameters for listing ceremony instances.
type ListCeremoniesQuery struct {
	CeremonyID   string
	StatusFilter string
	Limit        int32
	Offset       int32
}

// ListCeremoniesResult wraps a page of ceremonies with total count for pagination.
type ListCeremoniesResult struct {
	Ceremonies []ports.CeremonyResult
	TotalCount int32
}

// ListCeremoniesHandler handles ceremony listing queries.
type ListCeremoniesHandler struct {
	ceremony ports.CeremonyClient
}

// NewListCeremoniesHandler wires the handler to the ceremony port.
func NewListCeremoniesHandler(c ports.CeremonyClient) *ListCeremoniesHandler {
	return &ListCeremoniesHandler{ceremony: c}
}

// Handle executes the query, applying default pagination if limits are not set.
func (h *ListCeremoniesHandler) Handle(ctx context.Context, q ListCeremoniesQuery) (ListCeremoniesResult, error) {
	limit := q.Limit
	if limit <= 0 {
		limit = 50
	}

	offset := max(q.Offset, 0)

	ceremonies, total, err := h.ceremony.ListCeremonies(ctx, q.CeremonyID, q.StatusFilter, limit, offset)
	if err != nil {
		return ListCeremoniesResult{}, err
	}

	return ListCeremoniesResult{
		Ceremonies: ceremonies,
		TotalCount: total,
	}, nil
}
