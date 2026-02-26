package query

import (
	"context"
	"errors"
	"strings"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

func TestListEpicsHandler_Handle(t *testing.T) {
	t.Parallel()

	sampleEpics := []ports.EpicResult{
		{EpicID: "epic-1", ProjectID: "proj-1", Title: "Epic One", Status: "active"},
		{EpicID: "epic-2", ProjectID: "proj-1", Title: "Epic Two", Status: "done"},
	}

	tests := []struct {
		name      string
		query     ListEpicsQuery
		planning  *fakePlanningClient
		wantErr   bool
		errSubstr string
		wantCount int
		wantTotal int32
	}{
		{
			name:  "successful listing",
			query: ListEpicsQuery{ProjectID: "proj-1", Limit: 10},
			planning: &fakePlanningClient{
				epics:     sampleEpics,
				epicTotal: 2,
			},
			wantCount: 2,
			wantTotal: 2,
		},
		{
			name:      "missing project ID",
			query:     ListEpicsQuery{ProjectID: "", Limit: 10},
			planning:  &fakePlanningClient{},
			wantErr:   true,
			errSubstr: "project ID is required",
		},
		{
			name:  "default pagination",
			query: ListEpicsQuery{ProjectID: "proj-1", Limit: 0},
			planning: &fakePlanningClient{
				epics:     sampleEpics,
				epicTotal: 2,
			},
			wantCount: 2,
			wantTotal: 2,
		},
		{
			name:  "planning client error",
			query: ListEpicsQuery{ProjectID: "proj-1", Limit: 10},
			planning: &fakePlanningClient{
				epicErr: errors.New("project not found"),
			},
			wantErr:   true,
			errSubstr: "project not found",
		},
		{
			name:  "with status filter",
			query: ListEpicsQuery{ProjectID: "proj-1", StatusFilter: "active", Limit: 10},
			planning: &fakePlanningClient{
				epics:     sampleEpics[:1],
				epicTotal: 1,
			},
			wantCount: 1,
			wantTotal: 1,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			handler := NewListEpicsHandler(tt.planning)

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

			if len(result.Epics) != tt.wantCount {
				t.Errorf("Epics count = %d, want %d", len(result.Epics), tt.wantCount)
			}

			if result.TotalCount != tt.wantTotal {
				t.Errorf("TotalCount = %d, want %d", result.TotalCount, tt.wantTotal)
			}
		})
	}
}
