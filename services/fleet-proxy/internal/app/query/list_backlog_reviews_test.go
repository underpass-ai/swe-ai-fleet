package query

import (
	"context"
	"errors"
	"strings"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

func TestListBacklogReviewsHandler_Handle(t *testing.T) {
	t.Parallel()

	sampleReviews := []ports.BacklogReviewResult{
		{CeremonyID: "cer-1", Status: "IN_PROGRESS"},
		{CeremonyID: "cer-2", Status: "COMPLETED"},
	}

	tests := []struct {
		name      string
		query     ListBacklogReviewsQuery
		planning  *fakePlanningClient
		wantErr   bool
		errSubstr string
		wantCount int
		wantTotal int32
	}{
		{
			name:  "successful listing",
			query: ListBacklogReviewsQuery{Limit: 10, Offset: 0},
			planning: &fakePlanningClient{
				backlogReviews:     sampleReviews,
				backlogReviewTotal: 2,
			},
			wantCount: 2,
			wantTotal: 2,
		},
		{
			name:  "default pagination when limit is zero",
			query: ListBacklogReviewsQuery{Limit: 0, Offset: 0},
			planning: &fakePlanningClient{
				backlogReviews:     sampleReviews,
				backlogReviewTotal: 2,
			},
			wantCount: 2,
			wantTotal: 2,
		},
		{
			name:  "negative limit defaults to 50",
			query: ListBacklogReviewsQuery{Limit: -5, Offset: 0},
			planning: &fakePlanningClient{
				backlogReviews:     nil,
				backlogReviewTotal: 0,
			},
			wantCount: 0,
			wantTotal: 0,
		},
		{
			name:  "negative offset defaults to 0",
			query: ListBacklogReviewsQuery{Limit: 10, Offset: -1},
			planning: &fakePlanningClient{
				backlogReviews:     sampleReviews,
				backlogReviewTotal: 2,
			},
			wantCount: 2,
			wantTotal: 2,
		},
		{
			name:  "with status filter",
			query: ListBacklogReviewsQuery{StatusFilter: "IN_PROGRESS", Limit: 10},
			planning: &fakePlanningClient{
				backlogReviews:     sampleReviews[:1],
				backlogReviewTotal: 1,
			},
			wantCount: 1,
			wantTotal: 1,
		},
		{
			name:  "planning client error",
			query: ListBacklogReviewsQuery{Limit: 10},
			planning: &fakePlanningClient{
				backlogReviewListErr: errors.New("database connection lost"),
			},
			wantErr:   true,
			errSubstr: "database connection lost",
		},
		{
			name:  "empty result",
			query: ListBacklogReviewsQuery{Limit: 10},
			planning: &fakePlanningClient{
				backlogReviews:     nil,
				backlogReviewTotal: 0,
			},
			wantCount: 0,
			wantTotal: 0,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			handler := NewListBacklogReviewsHandler(tt.planning)

			result, err := handler.Handle(context.Background(), tt.query)

			if tt.wantErr {
				if err == nil {
					t.Fatalf("Handle() expected error containing %q, got nil", tt.errSubstr)
				}
				if !strings.Contains(err.Error(), tt.errSubstr) {
					t.Fatalf("Handle() error = %q, want substring %q", err.Error(), tt.errSubstr)
				}
				return
			}

			if err != nil {
				t.Fatalf("Handle() unexpected error: %v", err)
			}

			if len(result.Reviews) != tt.wantCount {
				t.Errorf("Reviews count = %d, want %d", len(result.Reviews), tt.wantCount)
			}

			if result.TotalCount != tt.wantTotal {
				t.Errorf("TotalCount = %d, want %d", result.TotalCount, tt.wantTotal)
			}
		})
	}
}
