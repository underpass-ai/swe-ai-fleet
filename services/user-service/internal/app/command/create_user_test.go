package command

import (
	"context"
	"errors"
	"strings"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/user-service/internal/domain"
)

func TestCreateUserHandler_Handle(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name      string
		cmd       CreateUserCmd
		seed      []domain.User // pre-populate the store
		storeErr  error         // force Create to fail with this error
		wantErr   bool
		errSubstr string
		checkRes  func(t *testing.T, res CreateUserResult)
	}{
		{
			name: "successful creation",
			cmd: CreateUserCmd{
				ClientID:    "spiffe://swe-ai-fleet/user/tirso/device/macbook",
				DeviceID:    "macbook",
				DisplayName: "Tirso",
				Email:       "tirso@example.com",
				Role:        "operator",
			},
			checkRes: func(t *testing.T, res CreateUserResult) {
				t.Helper()
				if !res.Created {
					t.Error("expected Created=true")
				}
				if res.User.ClientID != "spiffe://swe-ai-fleet/user/tirso/device/macbook" {
					t.Errorf("ClientID = %q", res.User.ClientID)
				}
				if res.User.DisplayName != "Tirso" {
					t.Errorf("DisplayName = %q", res.User.DisplayName)
				}
				if res.User.UserID == "" {
					t.Error("UserID should not be empty")
				}
			},
		},
		{
			name: "idempotent on existing client_id",
			cmd: CreateUserCmd{
				ClientID:    "spiffe://swe-ai-fleet/user/tirso/device/macbook",
				DeviceID:    "macbook",
				DisplayName: "Tirso Updated",
				Role:        "operator",
			},
			seed: []domain.User{
				{
					UserID:      "existing-uuid",
					ClientID:    "spiffe://swe-ai-fleet/user/tirso/device/macbook",
					DeviceID:    "macbook",
					DisplayName: "Tirso Original",
					Role:        "operator",
				},
			},
			checkRes: func(t *testing.T, res CreateUserResult) {
				t.Helper()
				if res.Created {
					t.Error("expected Created=false for existing client_id")
				}
				if res.User.UserID != "existing-uuid" {
					t.Errorf("UserID = %q, want existing-uuid", res.User.UserID)
				}
				if res.User.DisplayName != "Tirso Original" {
					t.Errorf("DisplayName = %q, want Tirso Original", res.User.DisplayName)
				}
			},
		},
		{
			name: "empty client_id",
			cmd: CreateUserCmd{
				ClientID:    "",
				DeviceID:    "macbook",
				DisplayName: "Tirso",
				Role:        "operator",
			},
			wantErr:   true,
			errSubstr: "client_id is required",
		},
		{
			name: "empty device_id",
			cmd: CreateUserCmd{
				ClientID:    "spiffe://swe-ai-fleet/user/tirso/device/macbook",
				DeviceID:    "",
				DisplayName: "Tirso",
				Role:        "operator",
			},
			wantErr:   true,
			errSubstr: "device_id is required",
		},
		{
			name: "empty display_name",
			cmd: CreateUserCmd{
				ClientID:    "spiffe://swe-ai-fleet/user/tirso/device/macbook",
				DeviceID:    "macbook",
				DisplayName: "",
				Role:        "operator",
			},
			wantErr:   true,
			errSubstr: "display_name is required",
		},
		{
			name: "invalid role",
			cmd: CreateUserCmd{
				ClientID:    "spiffe://swe-ai-fleet/user/tirso/device/macbook",
				DeviceID:    "macbook",
				DisplayName: "Tirso",
				Role:        "superadmin",
			},
			wantErr:   true,
			errSubstr: "role must be",
		},
		{
			name: "default role when empty",
			cmd: CreateUserCmd{
				ClientID:    "spiffe://swe-ai-fleet/user/tirso/device/macbook",
				DeviceID:    "macbook",
				DisplayName: "Tirso",
				Role:        "",
			},
			checkRes: func(t *testing.T, res CreateUserResult) {
				t.Helper()
				if res.User.Role != "operator" {
					t.Errorf("Role = %q, want operator", res.User.Role)
				}
			},
		},
		{
			name: "store error propagates",
			cmd: CreateUserCmd{
				ClientID:    "spiffe://swe-ai-fleet/user/tirso/device/macbook",
				DeviceID:    "macbook",
				DisplayName: "Tirso",
				Role:        "operator",
			},
			storeErr:  errors.New("database unavailable"),
			wantErr:   true,
			errSubstr: "database unavailable",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			writer := newFakeUserWriter()
			writer.createErr = tt.storeErr

			// Seed existing users.
			for _, u := range tt.seed {
				writer.users[u.UserID] = u
				writer.clientIdx[u.ClientID] = u.UserID
			}

			handler := NewCreateUserHandler(writer)
			res, err := handler.Handle(context.Background(), tt.cmd)

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
				tt.checkRes(t, res)
			}
		})
	}
}
