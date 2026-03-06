package ports

import "context"

// UserResult holds user profile data returned from the user-service.
type UserResult struct {
	UserID      string
	ClientID    string
	DeviceID    string
	DisplayName string
	Email       string
	Role        string
}

// UserClient is a port for communicating with the user-service.
type UserClient interface {
	// CreateUser creates or returns an existing user (idempotent on client_id).
	CreateUser(ctx context.Context, clientID, deviceID, displayName, email, role string) (UserResult, error)

	// GetUserByClientID retrieves a user by their SPIFFE client_id.
	GetUserByClientID(ctx context.Context, clientID string) (UserResult, error)
}
