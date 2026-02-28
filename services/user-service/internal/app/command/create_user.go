package command

import (
	"context"
	"errors"

	"github.com/underpass-ai/swe-ai-fleet/services/user-service/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/services/user-service/internal/domain"
)

// CreateUserCmd carries the parameters for creating a new user.
type CreateUserCmd struct {
	ClientID    string
	DeviceID    string
	DisplayName string
	Email       string
	Role        string
}

// CreateUserResult holds the output of a CreateUser operation.
type CreateUserResult struct {
	User    domain.User
	Created bool // true if newly created, false if already existed
}

// CreateUserHandler orchestrates user creation with idempotency on client_id.
type CreateUserHandler struct {
	writer ports.UserWriter
}

// NewCreateUserHandler wires the handler to its command-side port.
func NewCreateUserHandler(w ports.UserWriter) *CreateUserHandler {
	return &CreateUserHandler{writer: w}
}

// Handle creates a new user or returns the existing one if client_id already exists.
func (h *CreateUserHandler) Handle(ctx context.Context, cmd CreateUserCmd) (CreateUserResult, error) {
	user, err := domain.NewUser(cmd.ClientID, cmd.DeviceID, cmd.DisplayName, cmd.Email, cmd.Role)
	if err != nil {
		return CreateUserResult{}, err
	}

	if createErr := h.writer.Create(ctx, user); createErr != nil {
		if errors.Is(createErr, domain.ErrDuplicateClientID) {
			existing, getErr := h.writer.GetByClientID(ctx, cmd.ClientID)
			if getErr != nil {
				return CreateUserResult{}, getErr
			}
			return CreateUserResult{User: existing, Created: false}, nil
		}
		return CreateUserResult{}, createErr
	}

	return CreateUserResult{User: user, Created: true}, nil
}
