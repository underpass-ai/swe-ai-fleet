package event

import (
	"errors"
	"slices"
)

// EventFilter is a value object used to subscribe to or query a subset of
// fleet events. At least one filter criterion must be provided.
type EventFilter struct {
	// Types restricts the filter to events matching one of these types.
	// If empty, all event types are matched (provided ProjectID is set).
	Types []EventType

	// ProjectID restricts the filter to events within a specific project.
	// If nil, events from all projects are matched (provided Types is non-empty).
	ProjectID *string
}

// NewEventFilter creates a validated EventFilter.
// At least one of types or projectID must be provided.
func NewEventFilter(types []EventType, projectID *string) (EventFilter, error) {
	if len(types) == 0 && projectID == nil {
		return EventFilter{}, errors.New("event filter must have at least one criterion: types or project ID")
	}

	// Validate that all provided types are known.
	for _, t := range types {
		if !t.IsValid() {
			return EventFilter{}, errors.New("event filter contains invalid event type: " + string(t))
		}
	}

	// Validate projectID is non-empty if provided.
	if projectID != nil && *projectID == "" {
		return EventFilter{}, errors.New("project ID cannot be an empty string")
	}

	return EventFilter{
		Types:     types,
		ProjectID: projectID,
	}, nil
}

// Matches reports whether the given event matches this filter.
func (f EventFilter) Matches(evt FleetEvent) bool {
	if f.ProjectID != nil {
		// ProjectID filtering would require the event to carry a project ID.
		// This is a domain-level check; actual project extraction depends on
		// the event payload schema. For now, we only filter by type.
		// Infrastructure adapters should handle project-level routing.
	}

	if len(f.Types) > 0 {
		return slices.Contains(f.Types, evt.Type)
	}

	// No type filter means all types match.
	return true
}
