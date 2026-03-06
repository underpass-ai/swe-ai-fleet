// Package domain contains the core User entity, factory functions, and
// domain-level sentinel errors.
package domain

import (
	"errors"
	"time"

	"github.com/google/uuid"
)

// ErrNotFound signals that the requested entity does not exist.
var ErrNotFound = errors.New("not found")

// ErrDuplicateClientID signals that a user with the given client_id already exists.
var ErrDuplicateClientID = errors.New("duplicate client_id")

// User is the core domain entity representing a fleet operator.
type User struct {
	UserID      string
	ClientID    string
	DeviceID    string
	DisplayName string
	Email       string
	Role        string
	CreatedAt   time.Time
	UpdatedAt   time.Time
}

// NewUser creates a new User with a generated UUID and validated fields.
func NewUser(clientID, deviceID, displayName, email, role string) (User, error) {
	if clientID == "" {
		return User{}, errors.New("client_id is required")
	}
	if deviceID == "" {
		return User{}, errors.New("device_id is required")
	}
	if displayName == "" {
		return User{}, errors.New("display_name is required")
	}
	if role == "" {
		role = "operator"
	}
	if !isValidRole(role) {
		return User{}, errors.New("role must be operator, viewer, or admin")
	}

	now := time.Now().UTC()
	return User{
		UserID:      uuid.New().String(),
		ClientID:    clientID,
		DeviceID:    deviceID,
		DisplayName: displayName,
		Email:       email,
		Role:        role,
		CreatedAt:   now,
		UpdatedAt:   now,
	}, nil
}

func isValidRole(role string) bool {
	switch role {
	case "operator", "viewer", "admin":
		return true
	}
	return false
}
