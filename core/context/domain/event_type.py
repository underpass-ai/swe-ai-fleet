"""Domain event types as enum."""

from enum import Enum


class EventType(str, Enum):
    """Types of domain events in the Context bounded context.

    Using an enum ensures type safety and prevents typos in event handling.
    """

    # Story events
    STORY_CREATED = "story.created"  # Formerly case.created
    STORY_UPDATED = "story.updated"

    # Plan events
    PLAN_VERSIONED = "plan.versioned"

    # Task events (formerly subtask)
    TASK_CREATED = "task.created"  # Formerly subtask.created
    TASK_STATUS_CHANGED = "task.status_changed"  # Formerly subtask.status_changed
    TASK_ASSIGNED = "task.assigned"
    TASK_COMPLETED = "task.completed"

    # Decision events
    DECISION_MADE = "decision.made"
    DECISION_REVISED = "decision.revised"

    # Epic events
    EPIC_CREATED = "epic.created"
    EPIC_UPDATED = "epic.updated"

    def __str__(self) -> str:
        """Return the string value for event routing."""
        return self.value

