package ports

import (
	"context"

	"github.com/underpass-ai/swe-ai-fleet/services/user-service/internal/domain"
)

// UserReader is the query-side persistence port. It is used by query
// handlers that only read state, never mutate it.
type UserReader interface {
	// GetByID retrieves a user by user_id. Returns domain.ErrNotFound if missing.
	GetByID(ctx context.Context, userID string) (domain.User, error)

	// GetByClientID retrieves a user by client_id. Returns domain.ErrNotFound if missing.
	GetByClientID(ctx context.Context, clientID string) (domain.User, error)

	// List returns a paginated list of users with an optional role filter.
	List(ctx context.Context, roleFilter string, limit, offset int32) ([]domain.User, int32, error)
}
