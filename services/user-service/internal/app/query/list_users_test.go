package query

import (
	"context"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/user-service/internal/domain"
)

func TestListUsersHandler_Handle(t *testing.T) {
	t.Parallel()

	users := []domain.User{
		{UserID: "u1", ClientID: "c1", DisplayName: "Alice", Role: "operator"},
		{UserID: "u2", ClientID: "c2", DisplayName: "Bob", Role: "admin"},
		{UserID: "u3", ClientID: "c3", DisplayName: "Charlie", Role: "operator"},
	}

	tests := []struct {
		name       string
		roleFilter string
		limit      int32
		offset     int32
		wantCount  int
		wantTotal  int32
	}{
		{
			name:      "all users default limit",
			limit:     0, // should default to 100
			wantCount: 3,
			wantTotal: 3,
		},
		{
			name:       "filter by operator",
			roleFilter: "operator",
			limit:      100,
			wantCount:  2,
			wantTotal:  2,
		},
		{
			name:       "filter by admin",
			roleFilter: "admin",
			limit:      100,
			wantCount:  1,
			wantTotal:  1,
		},
		{
			name:       "filter no match",
			roleFilter: "viewer",
			limit:      100,
			wantCount:  0,
			wantTotal:  0,
		},
		{
			name:      "pagination limit",
			limit:     2,
			wantCount: 2,
			wantTotal: 3,
		},
		{
			name:      "pagination offset",
			limit:     100,
			offset:    2,
			wantCount: 1,
			wantTotal: 3,
		},
		{
			name:      "offset beyond total",
			limit:     100,
			offset:    10,
			wantCount: 0,
			wantTotal: 3,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			reader := newFakeUserReader()
			for _, u := range users {
				reader.seed(u)
			}

			handler := NewListUsersHandler(reader)
			result, total, err := handler.Handle(context.Background(), tt.roleFilter, tt.limit, tt.offset)

			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}

			if len(result) != tt.wantCount {
				t.Errorf("len(result) = %d, want %d", len(result), tt.wantCount)
			}
			if total != tt.wantTotal {
				t.Errorf("total = %d, want %d", total, tt.wantTotal)
			}
		})
	}
}
