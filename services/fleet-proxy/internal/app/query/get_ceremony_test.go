package query

import (
	"context"
	"errors"
	"strings"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

func TestGetCeremonyHandler_Handle(t *testing.T) {
	t.Parallel()

	sampleCeremony := ports.CeremonyResult{
		InstanceID:     "inst-1",
		CeremonyID:     "cer-1",
		DefinitionName: "planning",
		StoryID:        "story-1",
		Status:         "running",
		StepStatuses:   map[string]string{"step-1": "completed", "step-2": "pending"},
		CreatedAt:      "2024-01-01T00:00:00Z",
		UpdatedAt:      "2024-01-01T01:00:00Z",
	}

	tests := []struct {
		name       string
		query      GetCeremonyQuery
		ceremony   *fakeCeremonyClient
		wantErr    bool
		errSubstr  string
		wantResult ports.CeremonyResult
	}{
		{
			name:       "successful get",
			query:      GetCeremonyQuery{InstanceID: "inst-1"},
			ceremony:   &fakeCeremonyClient{ceremony: sampleCeremony},
			wantResult: sampleCeremony,
		},
		{
			name:      "missing instance ID",
			query:     GetCeremonyQuery{InstanceID: ""},
			ceremony:  &fakeCeremonyClient{},
			wantErr:   true,
			errSubstr: "instance ID is required",
		},
		{
			name:  "ceremony client error",
			query: GetCeremonyQuery{InstanceID: "inst-1"},
			ceremony: &fakeCeremonyClient{
				ceremonyErr: errors.New("instance not found"),
			},
			wantErr:   true,
			errSubstr: "instance not found",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			handler := NewGetCeremonyHandler(tt.ceremony)

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

			if result.InstanceID != tt.wantResult.InstanceID {
				t.Errorf("InstanceID = %q, want %q", result.InstanceID, tt.wantResult.InstanceID)
			}
			if result.CeremonyID != tt.wantResult.CeremonyID {
				t.Errorf("CeremonyID = %q, want %q", result.CeremonyID, tt.wantResult.CeremonyID)
			}
			if result.DefinitionName != tt.wantResult.DefinitionName {
				t.Errorf("DefinitionName = %q, want %q", result.DefinitionName, tt.wantResult.DefinitionName)
			}
			if result.Status != tt.wantResult.Status {
				t.Errorf("Status = %q, want %q", result.Status, tt.wantResult.Status)
			}
			if len(result.StepStatuses) != len(tt.wantResult.StepStatuses) {
				t.Errorf("StepStatuses length = %d, want %d", len(result.StepStatuses), len(tt.wantResult.StepStatuses))
			}
		})
	}
}
