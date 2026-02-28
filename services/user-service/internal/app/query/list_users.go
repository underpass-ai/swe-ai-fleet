package query

import (
	"context"

	"github.com/underpass-ai/swe-ai-fleet/services/user-service/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/services/user-service/internal/domain"
)

// ListUsersHandler retrieves a paginated list of users.
type ListUsersHandler struct {
	reader ports.UserReader
}

// NewListUsersHandler wires the handler to its query-side port.
func NewListUsersHandler(r ports.UserReader) *ListUsersHandler {
	return &ListUsersHandler{reader: r}
}

// Handle returns users matching the optional role filter.
func (h *ListUsersHandler) Handle(ctx context.Context, roleFilter string, limit, offset int32) ([]domain.User, int32, error) {
	if limit <= 0 {
		limit = 100
	}
	if offset < 0 {
		offset = 0
	}
	return h.reader.List(ctx, roleFilter, limit, offset)
}
