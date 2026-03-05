package domain

import (
	"strings"
	"testing"
)

func TestFleetEvent_Summary(t *testing.T) {
	tests := []struct {
		name     string
		event    FleetEvent
		contains []string // substrings that must appear in the summary
	}{
		{
			name: "story.created",
			event: FleetEvent{
				Type: "story.created", Timestamp: "2025-01-01T00:00:00Z",
				Producer: "agent-1", IdempotencyKey: "key-1",
			},
			contains: []string{"2025-01-01T00:00:00Z", "story created", "agent-1", "key=key-1"},
		},
		{
			name: "story.transitioned",
			event: FleetEvent{
				Type: "story.transitioned", Timestamp: "T1", CorrelationID: "corr-1",
			},
			contains: []string{"story transitioned", "corr=corr-1"},
		},
		{
			name: "task.assigned",
			event: FleetEvent{
				Type: "task.assigned", Timestamp: "T2", Producer: "scheduler",
				CorrelationID: "corr-2",
			},
			contains: []string{"task assigned", "scheduler", "corr=corr-2"},
		},
		{
			name: "task.completed",
			event: FleetEvent{
				Type: "task.completed", Timestamp: "T3", CorrelationID: "corr-3",
			},
			contains: []string{"task completed", "corr=corr-3"},
		},
		{
			name: "ceremony.started",
			event: FleetEvent{
				Type: "ceremony.started", Timestamp: "T4", Producer: "planner",
				CorrelationID: "corr-4",
			},
			contains: []string{"ceremony started", "planner", "corr=corr-4"},
		},
		{
			name: "ceremony.step_completed",
			event: FleetEvent{
				Type: "ceremony.step_completed", Timestamp: "T5", CorrelationID: "corr-5",
			},
			contains: []string{"ceremony step completed", "corr=corr-5"},
		},
		{
			name: "ceremony.completed",
			event: FleetEvent{
				Type: "ceremony.completed", Timestamp: "T6", CorrelationID: "corr-6",
			},
			contains: []string{"ceremony completed", "corr=corr-6"},
		},
		{
			name: "project.created",
			event: FleetEvent{
				Type: "project.created", Timestamp: "T7", Producer: "admin",
				IdempotencyKey: "key-7",
			},
			contains: []string{"project created", "admin", "key=key-7"},
		},
		{
			name: "backlog_review.started",
			event: FleetEvent{
				Type: "backlog_review.started", Timestamp: "T8", Producer: "po",
				CorrelationID: "corr-8",
			},
			contains: []string{"backlog review started", "po", "corr=corr-8"},
		},
		{
			name: "backlog_review.deliberation_complete",
			event: FleetEvent{
				Type: "backlog_review.deliberation_complete", Timestamp: "T9",
				CorrelationID: "corr-9",
			},
			contains: []string{"deliberation complete", "corr=corr-9"},
		},
		{
			name: "backlog_review.story_reviewed",
			event: FleetEvent{
				Type: "backlog_review.story_reviewed", Timestamp: "T10",
				CorrelationID: "corr-10",
			},
			contains: []string{"story reviewed", "corr=corr-10"},
		},
		{
			name: "backlog_review.completed",
			event: FleetEvent{
				Type: "backlog_review.completed", Timestamp: "T11",
				CorrelationID: "corr-11",
			},
			contains: []string{"backlog review completed", "corr=corr-11"},
		},
		{
			name: "backlog_review.cancelled",
			event: FleetEvent{
				Type: "backlog_review.cancelled", Timestamp: "T12",
				CorrelationID: "corr-12",
			},
			contains: []string{"backlog review cancelled", "corr=corr-12"},
		},
		{
			name: "rpc.inbound",
			event: FleetEvent{
				Type: "rpc.inbound", Timestamp: "T13", Producer: "ListStories",
				IdempotencyKey: "key-13",
			},
			contains: []string{"<-", "gRPC", "ListStories", "key=key-13"},
		},
		{
			name: "rpc.outbound",
			event: FleetEvent{
				Type: "rpc.outbound", Timestamp: "T14", Producer: "CreateTask",
				IdempotencyKey: "key-14",
			},
			contains: []string{"->", "gRPC", "CreateTask", "key=key-14"},
		},
		{
			name: "unknown type falls through to default",
			event: FleetEvent{
				Type: "custom.event", Timestamp: "T15", Producer: "x",
				CorrelationID: "corr-15",
			},
			contains: []string{"custom.event", "x", "corr=corr-15"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			summary := tt.event.Summary()
			for _, sub := range tt.contains {
				if !strings.Contains(summary, sub) {
					t.Errorf("Summary() = %q, missing substring %q", summary, sub)
				}
			}
		})
	}
}

func TestFleetEvent_Category(t *testing.T) {
	tests := []struct {
		name     string
		event    FleetEvent
		wantCat  string
	}{
		{
			name:    "rpc.inbound is grpc",
			event:   FleetEvent{Type: "rpc.inbound"},
			wantCat: "grpc",
		},
		{
			name:    "rpc.outbound is grpc",
			event:   FleetEvent{Type: "rpc.outbound"},
			wantCat: "grpc",
		},
		{
			name:    "deliberation.received is deliberation",
			event:   FleetEvent{Type: "deliberation.received"},
			wantCat: "deliberation",
		},
		{
			name:    "backlog_review.deliberation_complete is deliberation",
			event:   FleetEvent{Type: "backlog_review.deliberation_complete"},
			wantCat: "deliberation",
		},
		{
			name:    "story.created is domain",
			event:   FleetEvent{Type: "story.created"},
			wantCat: "domain",
		},
		{
			name:    "ceremony.started is domain",
			event:   FleetEvent{Type: "ceremony.started"},
			wantCat: "domain",
		},
		{
			name:    "unknown type is domain",
			event:   FleetEvent{Type: "something.else"},
			wantCat: "domain",
		},
		{
			name:    "backlog_review.started is domain (not deliberation)",
			event:   FleetEvent{Type: "backlog_review.started"},
			wantCat: "domain",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := tt.event.Category()
			if got != tt.wantCat {
				t.Errorf("Category() = %q, want %q", got, tt.wantCat)
			}
		})
	}
}
