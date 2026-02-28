package query

import (
	"context"
	"errors"
	"strings"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

func TestGetBacklogReviewHandler_Handle(t *testing.T) {
	t.Parallel()

	sampleReview := ports.BacklogReviewResult{
		CeremonyID: "cer-1",
		Status:     "IN_PROGRESS",
		CreatedBy:  "user-1",
		StoryIDs:   []string{"story-1", "story-2"},
	}

	tests := []struct {
		name       string
		query      GetBacklogReviewQuery
		planning   *fakePlanningClient
		wantErr    bool
		errSubstr  string
		wantResult ports.BacklogReviewResult
	}{
		{
			name:       "successful get",
			query:      GetBacklogReviewQuery{CeremonyID: "cer-1"},
			planning:   &fakePlanningClient{backlogReview: sampleReview},
			wantResult: sampleReview,
		},
		{
			name:      "missing ceremony ID",
			query:     GetBacklogReviewQuery{CeremonyID: ""},
			planning:  &fakePlanningClient{},
			wantErr:   true,
			errSubstr: "ceremony ID is required",
		},
		{
			name:  "planning client error",
			query: GetBacklogReviewQuery{CeremonyID: "cer-1"},
			planning: &fakePlanningClient{
				backlogReviewErr: errors.New("ceremony not found"),
			},
			wantErr:   true,
			errSubstr: "ceremony not found",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			handler := NewGetBacklogReviewHandler(tt.planning)

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

			if result.CeremonyID != tt.wantResult.CeremonyID {
				t.Errorf("CeremonyID = %q, want %q", result.CeremonyID, tt.wantResult.CeremonyID)
			}
			if result.Status != tt.wantResult.Status {
				t.Errorf("Status = %q, want %q", result.Status, tt.wantResult.Status)
			}
			if result.CreatedBy != tt.wantResult.CreatedBy {
				t.Errorf("CreatedBy = %q, want %q", result.CreatedBy, tt.wantResult.CreatedBy)
			}
			if len(result.StoryIDs) != len(tt.wantResult.StoryIDs) {
				t.Errorf("StoryIDs length = %d, want %d", len(result.StoryIDs), len(tt.wantResult.StoryIDs))
			}
		})
	}
}
