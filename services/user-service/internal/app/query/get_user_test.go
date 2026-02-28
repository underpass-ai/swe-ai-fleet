package query

import (
	"context"
	"strings"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/user-service/internal/domain"
)

func TestGetUserHandler_Handle(t *testing.T) {
	t.Parallel()

	seedUser := domain.User{
		UserID:      "user-123",
		ClientID:    "spiffe://swe-ai-fleet/user/tirso/device/macbook",
		DisplayName: "Tirso",
		Role:        "operator",
	}

	tests := []struct {
		name      string
		userID    string
		seed      *domain.User
		wantErr   bool
		errSubstr string
	}{
		{
			name:   "found",
			userID: "user-123",
			seed:   &seedUser,
		},
		{
			name:      "empty user_id",
			userID:    "",
			wantErr:   true,
			errSubstr: "user_id is required",
		},
		{
			name:      "not found",
			userID:    "nonexistent",
			wantErr:   true,
			errSubstr: "not found",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			reader := newFakeUserReader()
			if tt.seed != nil {
				reader.seed(*tt.seed)
			}

			handler := NewGetUserHandler(reader)
			user, err := handler.Handle(context.Background(), tt.userID)

			if tt.wantErr {
				if err == nil {
					t.Fatalf("expected error containing %q, got nil", tt.errSubstr)
				}
				if !strings.Contains(err.Error(), tt.errSubstr) {
					t.Fatalf("error = %q, want substring %q", err.Error(), tt.errSubstr)
				}
				return
			}

			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if user.UserID != tt.seed.UserID {
				t.Errorf("UserID = %q, want %q", user.UserID, tt.seed.UserID)
			}
		})
	}
}

func TestGetUserByClientIDHandler_Handle(t *testing.T) {
	t.Parallel()

	seedUser := domain.User{
		UserID:      "user-123",
		ClientID:    "spiffe://swe-ai-fleet/user/tirso/device/macbook",
		DisplayName: "Tirso",
		Role:        "operator",
	}

	tests := []struct {
		name      string
		clientID  string
		seed      *domain.User
		wantErr   bool
		errSubstr string
	}{
		{
			name:     "found",
			clientID: "spiffe://swe-ai-fleet/user/tirso/device/macbook",
			seed:     &seedUser,
		},
		{
			name:      "empty client_id",
			clientID:  "",
			wantErr:   true,
			errSubstr: "client_id is required",
		},
		{
			name:      "not found",
			clientID:  "spiffe://swe-ai-fleet/user/unknown/device/unknown",
			wantErr:   true,
			errSubstr: "not found",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			reader := newFakeUserReader()
			if tt.seed != nil {
				reader.seed(*tt.seed)
			}

			handler := NewGetUserByClientIDHandler(reader)
			user, err := handler.Handle(context.Background(), tt.clientID)

			if tt.wantErr {
				if err == nil {
					t.Fatalf("expected error containing %q, got nil", tt.errSubstr)
				}
				if !strings.Contains(err.Error(), tt.errSubstr) {
					t.Fatalf("error = %q, want substring %q", err.Error(), tt.errSubstr)
				}
				return
			}

			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if user.DisplayName != tt.seed.DisplayName {
				t.Errorf("DisplayName = %q, want %q", user.DisplayName, tt.seed.DisplayName)
			}
		})
	}
}
