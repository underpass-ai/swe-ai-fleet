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

	// EventBacklogReviewStarted is emitted when a backlog review ceremony starts.
	EventBacklogReviewStarted EventType = "backlog_review.started"

	// EventBacklogReviewDeliberationComplete is emitted when a council deliberation finishes.
	EventBacklogReviewDeliberationComplete EventType = "backlog_review.deliberation_complete"

	// EventBacklogReviewStoryReviewed is emitted when all councils finish reviewing a story.
	EventBacklogReviewStoryReviewed EventType = "backlog_review.story_reviewed"

	// EventBacklogReviewCompleted is emitted when a backlog review ceremony completes.
	EventBacklogReviewCompleted EventType = "backlog_review.completed"

	// EventBacklogReviewCancelled is emitted when a backlog review ceremony is cancelled.
	EventBacklogReviewCancelled EventType = "backlog_review.cancelled"

	// EventRPCInbound is emitted when a gRPC request is received by fleet-proxy.
	EventRPCInbound EventType = "rpc.inbound"

	// EventRPCOutbound is emitted when fleet-proxy makes an outbound gRPC call.
	EventRPCOutbound EventType = "rpc.outbound"
)

// knownEventTypes is the set of all valid event types.
var knownEventTypes = map[EventType]struct{}{
	EventStoryCreated:                      {},
	EventStoryTransitioned:                 {},
	EventTaskCreated:                       {},
	EventCeremonyStarted:                   {},
	EventCeremonyCompleted:                 {},
	EventDeliberationReceived:              {},
	EventBacklogReviewStarted:              {},
	EventBacklogReviewDeliberationComplete: {},
	EventBacklogReviewStoryReviewed:        {},
	EventBacklogReviewCompleted:            {},
	EventBacklogReviewCancelled:            {},
	EventRPCInbound:                        {},
	EventRPCOutbound:                       {},
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
