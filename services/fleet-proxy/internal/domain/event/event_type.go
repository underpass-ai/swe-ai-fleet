package event

import "fmt"

// EventType is a value object representing the type of a fleet event.
// It uses a string-based enum for extensibility while maintaining validation.
type EventType string

const (
	// EventStoryCreated is emitted when a new story is added to the backlog.
	EventStoryCreated EventType = "story.created"

	// EventStoryTransitioned is emitted when a story moves between states.
	EventStoryTransitioned EventType = "story.transitioned"

	// EventTaskCreated is emitted when a task is derived from a story.
	EventTaskCreated EventType = "task.created"

	// EventCeremonyStarted is emitted when a scrum ceremony begins.
	EventCeremonyStarted EventType = "ceremony.started"

	// EventCeremonyCompleted is emitted when a scrum ceremony finishes.
	EventCeremonyCompleted EventType = "ceremony.completed"

	// EventDeliberationReceived is emitted when an agent deliberation is recorded.
	EventDeliberationReceived EventType = "deliberation.received"
)

// knownEventTypes is the set of all valid event types.
var knownEventTypes = map[EventType]struct{}{
	EventStoryCreated:         {},
	EventStoryTransitioned:    {},
	EventTaskCreated:          {},
	EventCeremonyStarted:      {},
	EventCeremonyCompleted:    {},
	EventDeliberationReceived: {},
}

// String returns the string representation of the event type.
func (t EventType) String() string {
	return string(t)
}

// IsValid reports whether the event type is one of the known constants.
func (t EventType) IsValid() bool {
	_, ok := knownEventTypes[t]
	return ok
}

// ParseEventType converts a string to an EventType and validates it.
func ParseEventType(s string) (EventType, error) {
	t := EventType(s)
	if !t.IsValid() {
		return "", fmt.Errorf("unknown event type %q", s)
	}
	return t, nil
}
