package command

import (
	"context"
	"errors"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/user-service/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/services/user-service/internal/domain"
)

// UpdateUserCmd carries the parameters for updating an existing user.
type UpdateUserCmd struct {
	UserID      string
	DisplayName string
	Email       string
	Role        string
}

// UpdateUserHandler orchestrates partial user updates.
type UpdateUserHandler struct {
	writer ports.UserWriter
}

// NewUpdateUserHandler wires the handler to its command-side port.
func NewUpdateUserHandler(w ports.UserWriter) *UpdateUserHandler {
	return &UpdateUserHandler{writer: w}
}

// Handle applies partial updates to an existing user. Only non-empty fields are changed.
func (h *UpdateUserHandler) Handle(ctx context.Context, cmd UpdateUserCmd) (domain.User, error) {
	if cmd.UserID == "" {
		return domain.User{}, errors.New("user_id is required")
	}

	user, err := h.writer.GetByID(ctx, cmd.UserID)
	if err != nil {
		return domain.User{}, err
	}

	if cmd.DisplayName != "" {
		user.DisplayName = cmd.DisplayName
	}
	if cmd.Email != "" {
		user.Email = cmd.Email
	}
	if cmd.Role != "" {
		user.Role = cmd.Role
	}
	user.UpdatedAt = time.Now().UTC()

	if err := h.writer.Update(ctx, user); err != nil {
		return domain.User{}, err
	}

	return user, nil
}
