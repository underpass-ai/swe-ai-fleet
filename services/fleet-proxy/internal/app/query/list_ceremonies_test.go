package query

import (
	"context"
	"errors"
	"strings"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
)

func TestListCeremoniesHandler_Handle(t *testing.T) {
	t.Parallel()

	sampleCeremonies := []ports.CeremonyResult{
		{InstanceID: "inst-1", CeremonyID: "cer-1", Status: "running"},
		{InstanceID: "inst-2", CeremonyID: "cer-1", Status: "completed"},
	}

	tests := []struct {
		name      string
		query     ListCeremoniesQuery
		ceremony  *fakeCeremonyClient
		wantErr   bool
		errSubstr string
		wantCount int
		wantTotal int32
	}{
		{
			name:  "successful listing",
			query: ListCeremoniesQuery{CeremonyID: "cer-1", Limit: 10},
			ceremony: &fakeCeremonyClient{
				ceremonies:   sampleCeremonies,
				ceremonyList: 2,
			},
			wantCount: 2,
			wantTotal: 2,
		},
		{
			name:  "default pagination when limit is zero",
			query: ListCeremoniesQuery{CeremonyID: "cer-1", Limit: 0},
			ceremony: &fakeCeremonyClient{
				ceremonies:   sampleCeremonies,
				ceremonyList: 2,
			},
			wantCount: 2,
			wantTotal: 2,
		},
		{
			name:  "negative limit defaults to 50",
			query: ListCeremoniesQuery{CeremonyID: "cer-1", Limit: -3},
			ceremony: &fakeCeremonyClient{
				ceremonies:   nil,
				ceremonyList: 0,
			},
			wantCount: 0,
			wantTotal: 0,
		},
		{
			name:  "with status filter",
			query: ListCeremoniesQuery{CeremonyID: "cer-1", StatusFilter: "running", Limit: 10},
			ceremony: &fakeCeremonyClient{
				ceremonies:   sampleCeremonies[:1],
				ceremonyList: 1,
			},
			wantCount: 1,
			wantTotal: 1,
		},
		{
			name:  "ceremony client error",
			query: ListCeremoniesQuery{CeremonyID: "cer-1", Limit: 10},
			ceremony: &fakeCeremonyClient{
				listErr: errors.New("ceremony service down"),
			},
			wantErr:   true,
			errSubstr: "ceremony service down",
		},
		{
			name:  "empty ceremony ID is allowed",
			query: ListCeremoniesQuery{CeremonyID: "", Limit: 10},
			ceremony: &fakeCeremonyClient{
				ceremonies:   sampleCeremonies,
				ceremonyList: 2,
			},
			wantCount: 2,
			wantTotal: 2,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			handler := NewListCeremoniesHandler(tt.ceremony)

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

			if len(result.Ceremonies) != tt.wantCount {
				t.Errorf("Ceremonies count = %d, want %d", len(result.Ceremonies), tt.wantCount)
			}

			if result.TotalCount != tt.wantTotal {
				t.Errorf("TotalCount = %d, want %d", result.TotalCount, tt.wantTotal)
			}
		})
	}
}
