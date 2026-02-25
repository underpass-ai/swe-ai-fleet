package query

import (
	"context"
	"errors"
	"strings"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

func TestListProjectsHandler_Handle(t *testing.T) {
	t.Parallel()

	sampleProjects := []ports.ProjectResult{
		{ProjectID: "proj-1", Name: "Alpha", Status: "active"},
		{ProjectID: "proj-2", Name: "Beta", Status: "active"},
	}

	tests := []struct {
		name       string
		query      ListProjectsQuery
		planning   *fakePlanningClient
		wantErr    bool
		errSubstr  string
		wantCount  int
		wantTotal  int32
	}{
		{
			name:  "successful listing",
			query: ListProjectsQuery{Limit: 10, Offset: 0},
			planning: &fakePlanningClient{
				projects:     sampleProjects,
				projectTotal: 2,
			},
			wantCount: 2,
			wantTotal: 2,
		},
		{
			name:  "default pagination when limit is zero",
			query: ListProjectsQuery{Limit: 0, Offset: 0},
			planning: &fakePlanningClient{
				projects:     sampleProjects,
				projectTotal: 2,
			},
			wantCount: 2,
			wantTotal: 2,
		},
		{
			name:  "negative limit defaults to 50",
			query: ListProjectsQuery{Limit: -5, Offset: 0},
			planning: &fakePlanningClient{
				projects:     nil,
				projectTotal: 0,
			},
			wantCount: 0,
			wantTotal: 0,
		},
		{
			name:  "negative offset defaults to 0",
			query: ListProjectsQuery{Limit: 10, Offset: -1},
			planning: &fakePlanningClient{
				projects:     sampleProjects,
				projectTotal: 2,
			},
			wantCount: 2,
			wantTotal: 2,
		},
		{
			name:  "with status filter",
			query: ListProjectsQuery{StatusFilter: "active", Limit: 10},
			planning: &fakePlanningClient{
				projects:     sampleProjects[:1],
				projectTotal: 1,
			},
			wantCount: 1,
			wantTotal: 1,
		},
		{
			name:  "planning client error",
			query: ListProjectsQuery{Limit: 10},
			planning: &fakePlanningClient{
				projectErr: errors.New("database connection lost"),
			},
			wantErr:   true,
			errSubstr: "database connection lost",
		},
		{
			name:  "empty result",
			query: ListProjectsQuery{Limit: 10},
			planning: &fakePlanningClient{
				projects:     nil,
				projectTotal: 0,
			},
			wantCount: 0,
			wantTotal: 0,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			handler := NewListProjectsHandler(tt.planning)

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

			if len(result.Projects) != tt.wantCount {
				t.Errorf("Projects count = %d, want %d", len(result.Projects), tt.wantCount)
			}

			if result.TotalCount != tt.wantTotal {
				t.Errorf("TotalCount = %d, want %d", result.TotalCount, tt.wantTotal)
			}
		})
	}
}
