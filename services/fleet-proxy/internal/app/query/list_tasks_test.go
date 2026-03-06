package query

import (
	"context"
	"errors"
	"strings"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

func TestListTasksHandler_Handle(t *testing.T) {
	t.Parallel()

	sampleTasks := []ports.TaskResult{
		{TaskID: "task-1", StoryID: "story-1", Title: "Task One", Type: "development", Status: "pending"},
		{TaskID: "task-2", StoryID: "story-1", Title: "Task Two", Type: "review", Status: "done"},
	}

	tests := []struct {
		name      string
		query     ListTasksQuery
		planning  *fakePlanningClient
		wantErr   bool
		errSubstr string
		wantCount int
		wantTotal int32
	}{
		{
			name:  "successful listing",
			query: ListTasksQuery{StoryID: "story-1", Limit: 10},
			planning: &fakePlanningClient{
				tasks:     sampleTasks,
				taskTotal: 2,
			},
			wantCount: 2,
			wantTotal: 2,
		},
		{
			name:      "missing story ID",
			query:     ListTasksQuery{StoryID: "", Limit: 10},
			planning:  &fakePlanningClient{},
			wantErr:   true,
			errSubstr: "story ID is required",
		},
		{
			name:  "default pagination",
			query: ListTasksQuery{StoryID: "story-1", Limit: 0},
			planning: &fakePlanningClient{
				tasks:     sampleTasks,
				taskTotal: 2,
			},
			wantCount: 2,
			wantTotal: 2,
		},
		{
			name:  "planning client error",
			query: ListTasksQuery{StoryID: "story-1", Limit: 10},
			planning: &fakePlanningClient{
				taskErr: errors.New("story not found"),
			},
			wantErr:   true,
			errSubstr: "story not found",
		},
		{
			name:  "with status filter",
			query: ListTasksQuery{StoryID: "story-1", StatusFilter: "pending", Limit: 10},
			planning: &fakePlanningClient{
				tasks:     sampleTasks[:1],
				taskTotal: 1,
			},
			wantCount: 1,
			wantTotal: 1,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			handler := NewListTasksHandler(tt.planning)

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

			if len(result.Tasks) != tt.wantCount {
				t.Errorf("Tasks count = %d, want %d", len(result.Tasks), tt.wantCount)
			}

			if result.TotalCount != tt.wantTotal {
				t.Errorf("TotalCount = %d, want %d", result.TotalCount, tt.wantTotal)
			}
		})
	}
}
