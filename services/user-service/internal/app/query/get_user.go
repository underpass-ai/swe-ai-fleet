package query

import (
	"context"
	"errors"

	"github.com/underpass-ai/swe-ai-fleet/services/user-service/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/services/user-service/internal/domain"
)

// GetUserHandler retrieves a user by user_id.
type GetUserHandler struct {
	reader ports.UserReader
}

// NewGetUserHandler wires the handler to its query-side port.
func NewGetUserHandler(r ports.UserReader) *GetUserHandler {
	return &GetUserHandler{reader: r}
}

// Handle retrieves a user by user_id.
func (h *GetUserHandler) Handle(ctx context.Context, userID string) (domain.User, error) {
	if userID == "" {
		return domain.User{}, errors.New("user_id is required")
	}
	return h.reader.GetByID(ctx, userID)
}

// GetUserByClientIDHandler retrieves a user by their SPIFFE client_id.
type GetUserByClientIDHandler struct {
	reader ports.UserReader
}

// NewGetUserByClientIDHandler wires the handler to its query-side port.
func NewGetUserByClientIDHandler(r ports.UserReader) *GetUserByClientIDHandler {
	return &GetUserByClientIDHandler{reader: r}
}

// Handle retrieves a user by client_id.
func (h *GetUserByClientIDHandler) Handle(ctx context.Context, clientID string) (domain.User, error) {
	if clientID == "" {
		return domain.User{}, errors.New("client_id is required")
	}
	return h.reader.GetByClientID(ctx, clientID)
}
