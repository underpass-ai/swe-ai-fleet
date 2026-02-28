package command

import (
	"context"
	"errors"
	"strings"
	"testing"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/user-service/internal/domain"
)

func TestUpdateUserHandler_Handle(t *testing.T) {
	t.Parallel()

	seedUser := domain.User{
		UserID:      "user-123",
		ClientID:    "spiffe://swe-ai-fleet/user/tirso/device/macbook",
		DeviceID:    "macbook",
		DisplayName: "Tirso",
		Email:       "tirso@example.com",
		Role:        "operator",
		CreatedAt:   time.Now().UTC(),
		UpdatedAt:   time.Now().UTC(),
	}

	tests := []struct {
		name      string
		cmd       UpdateUserCmd
		seed      *domain.User
		storeErr  error
		wantErr   bool
		errSubstr string
		checkRes  func(t *testing.T, user domain.User)
	}{
		{
			name: "update display name",
			cmd:  UpdateUserCmd{UserID: "user-123", DisplayName: "Tirso Updated"},
			seed: &seedUser,
			checkRes: func(t *testing.T, user domain.User) {
				t.Helper()
				if user.DisplayName != "Tirso Updated" {
					t.Errorf("DisplayName = %q, want Tirso Updated", user.DisplayName)
				}
				if user.Email != "tirso@example.com" {
					t.Error("Email should not change")
				}
			},
		},
		{
			name: "update email",
			cmd:  UpdateUserCmd{UserID: "user-123", Email: "new@example.com"},
			seed: &seedUser,
			checkRes: func(t *testing.T, user domain.User) {
				t.Helper()
				if user.Email != "new@example.com" {
					t.Errorf("Email = %q, want new@example.com", user.Email)
				}
			},
		},
		{
			name: "update role",
			cmd:  UpdateUserCmd{UserID: "user-123", Role: "admin"},
			seed: &seedUser,
			checkRes: func(t *testing.T, user domain.User) {
				t.Helper()
				if user.Role != "admin" {
					t.Errorf("Role = %q, want admin", user.Role)
				}
			},
		},
		{
			name:      "empty user_id",
			cmd:       UpdateUserCmd{UserID: "", DisplayName: "X"},
			wantErr:   true,
			errSubstr: "user_id is required",
		},
		{
			name:      "user not found",
			cmd:       UpdateUserCmd{UserID: "nonexistent", DisplayName: "X"},
			wantErr:   true,
			errSubstr: "not found",
		},
		{
			name:      "store update error",
			cmd:       UpdateUserCmd{UserID: "user-123", DisplayName: "X"},
			seed:      &seedUser,
			storeErr:  errors.New("disk full"),
			wantErr:   true,
			errSubstr: "disk full",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			writer := newFakeUserWriter()
			writer.updateErr = tt.storeErr

			if tt.seed != nil {
				writer.users[tt.seed.UserID] = *tt.seed
				writer.clientIdx[tt.seed.ClientID] = tt.seed.UserID
			}

			handler := NewUpdateUserHandler(writer)
			user, err := handler.Handle(context.Background(), tt.cmd)

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

			if tt.checkRes != nil {
				tt.checkRes(t, user)
			}
		})
	}
}
