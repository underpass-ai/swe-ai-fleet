package query

import (
	"context"
	"errors"
	"strings"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

func TestListStoriesHandler_Handle(t *testing.T) {
	t.Parallel()

	sampleStories := []ports.StoryResult{
		{StoryID: "story-1", EpicID: "epic-1", Title: "Story One", State: "backlog"},
		{StoryID: "story-2", EpicID: "epic-1", Title: "Story Two", State: "in_progress"},
	}

	tests := []struct {
		name      string
		query     ListStoriesQuery
		planning  *fakePlanningClient
		wantErr   bool
		errSubstr string
		wantCount int
		wantTotal int32
	}{
		{
			name:  "successful listing",
			query: ListStoriesQuery{EpicID: "epic-1", Limit: 10},
			planning: &fakePlanningClient{
				stories:    sampleStories,
				storyTotal: 2,
			},
			wantCount: 2,
			wantTotal: 2,
		},
		{
			name:      "missing epic ID",
			query:     ListStoriesQuery{EpicID: "", Limit: 10},
			planning:  &fakePlanningClient{},
			wantErr:   true,
			errSubstr: "epic ID is required",
		},
		{
			name:  "default pagination",
			query: ListStoriesQuery{EpicID: "epic-1", Limit: 0},
			planning: &fakePlanningClient{
				stories:    sampleStories,
				storyTotal: 2,
			},
			wantCount: 2,
			wantTotal: 2,
		},
		{
			name:  "planning client error",
			query: ListStoriesQuery{EpicID: "epic-1", Limit: 10},
			planning: &fakePlanningClient{
				storyErr: errors.New("epic not found"),
			},
			wantErr:   true,
			errSubstr: "epic not found",
		},
		{
			name:  "with state filter",
			query: ListStoriesQuery{EpicID: "epic-1", StateFilter: "backlog", Limit: 10},
			planning: &fakePlanningClient{
				stories:    sampleStories[:1],
				storyTotal: 1,
			},
			wantCount: 1,
			wantTotal: 1,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			handler := NewListStoriesHandler(tt.planning)

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

			if len(result.Stories) != tt.wantCount {
				t.Errorf("Stories count = %d, want %d", len(result.Stories), tt.wantCount)
			}

			if result.TotalCount != tt.wantTotal {
				t.Errorf("TotalCount = %d, want %d", result.TotalCount, tt.wantTotal)
			}
		})
	}
}
