package event

import (
	"strings"
	"testing"
)

func TestParseEventType(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name      string
		input     string
		wantType  EventType
		wantErr   bool
		errSubstr string
	}{
		{
			name:     "story.created",
			input:    "story.created",
			wantType: EventStoryCreated,
		},
		{
			name:     "story.transitioned",
			input:    "story.transitioned",
			wantType: EventStoryTransitioned,
		},
		{
			name:     "task.created",
			input:    "task.created",
			wantType: EventTaskCreated,
		},
		{
			name:     "ceremony.started",
			input:    "ceremony.started",
			wantType: EventCeremonyStarted,
		},
		{
			name:     "ceremony.completed",
			input:    "ceremony.completed",
			wantType: EventCeremonyCompleted,
		},
		{
			name:     "deliberation.received",
			input:    "deliberation.received",
			wantType: EventDeliberationReceived,
		},
		{
			name:      "empty string",
			input:     "",
			wantErr:   true,
			errSubstr: "unknown event type",
		},
		{
			name:      "unknown type",
			input:     "story.deleted",
			wantErr:   true,
			errSubstr: "unknown event type",
		},
		{
			name:      "uppercase is invalid",
			input:     "Story.Created",
			wantErr:   true,
			errSubstr: "unknown event type",
		},
		{
			name:      "partial match is invalid",
			input:     "story",
			wantErr:   true,
			errSubstr: "unknown event type",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			got, err := ParseEventType(tt.input)

			if tt.wantErr {
				if err == nil {
					t.Fatalf("ParseEventType(%q) expected error containing %q, got nil", tt.input, tt.errSubstr)
				}
				if !strings.Contains(err.Error(), tt.errSubstr) {
					t.Fatalf("ParseEventType(%q) error = %q, want substring %q", tt.input, err.Error(), tt.errSubstr)
				}
				return
			}

			if err != nil {
				t.Fatalf("ParseEventType(%q) unexpected error: %v", tt.input, err)
			}

			if got != tt.wantType {
				t.Errorf("ParseEventType(%q) = %q, want %q", tt.input, got, tt.wantType)
			}
		})
	}
}

func TestEventType_IsValid(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name  string
		et    EventType
		valid bool
	}{
		{"story.created is valid", EventStoryCreated, true},
		{"story.transitioned is valid", EventStoryTransitioned, true},
		{"task.created is valid", EventTaskCreated, true},
		{"ceremony.started is valid", EventCeremonyStarted, true},
		{"ceremony.completed is valid", EventCeremonyCompleted, true},
		{"deliberation.received is valid", EventDeliberationReceived, true},
		{"empty is invalid", EventType(""), false},
		{"unknown is invalid", EventType("unknown.event"), false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			if got := tt.et.IsValid(); got != tt.valid {
				t.Errorf("EventType(%q).IsValid() = %v, want %v", tt.et, got, tt.valid)
			}
		})
	}
}

func TestEventType_String(t *testing.T) {
	t.Parallel()

	if got := EventStoryCreated.String(); got != "story.created" {
		t.Errorf("EventStoryCreated.String() = %q, want %q", got, "story.created")
	}

	custom := EventType("custom.type")
	if got := custom.String(); got != "custom.type" {
		t.Errorf("EventType(\"custom.type\").String() = %q, want %q", got, "custom.type")
	}
}
