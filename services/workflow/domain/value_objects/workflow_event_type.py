"""Workflow event type enumeration.

Defines all event types published by the workflow service.
Following Domain-Driven Design principles.
"""

from enum import Enum


class WorkflowEventType(str, Enum):
    """Workflow event types.

    Domain knowledge: What events does the workflow system publish?

    Events follow naming convention: workflow.{resource}.{action}
    """

    # State transition events
    STATE_CHANGED = "workflow.state.changed"

    # Assignment events
    TASK_ASSIGNED = "workflow.task.assigned"

    # Validation events
    VALIDATION_REQUIRED = "workflow.validation.required"

    # Completion events
    TASK_COMPLETED = "workflow.task.completed"
    TASK_CANCELLED = "workflow.task.cancelled"

    def __str__(self) -> str:
        """String representation (returns the event name)."""
        return self.value

