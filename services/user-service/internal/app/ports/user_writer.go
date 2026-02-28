// Package ports defines the driven-side interfaces (secondary ports) for the
// user-service application layer, following CQRS separation.
package ports

import (
	"context"

	"github.com/underpass-ai/swe-ai-fleet/services/user-service/internal/domain"
)

// UserWriter is the command-side persistence port. It is used by command
// handlers that mutate state (create, update). Read methods are included
// because commands need them for idempotency checks and read-modify-write.
type UserWriter interface {
	// Create persists a new user. Returns domain.ErrDuplicateClientID if client_id exists.
	Create(ctx context.Context, user domain.User) error

	// GetByID retrieves a user by user_id. Returns domain.ErrNotFound if missing.
	GetByID(ctx context.Context, userID string) (domain.User, error)

	// GetByClientID retrieves a user by client_id. Returns domain.ErrNotFound if missing.
	GetByClientID(ctx context.Context, clientID string) (domain.User, error)

	// Update persists changes to an existing user. Returns domain.ErrNotFound if missing.
	Update(ctx context.Context, user domain.User) error
}
