"""TaskStatusChangedEvent - Domain event for task status changes."""

from dataclasses import dataclass

from core.context.domain.domain_event import DomainEvent
from core.context.domain.entity_ids.task_id import TaskId
from core.context.domain.event_type import EventType
from core.context.domain.task_status import TaskStatus


@dataclass(frozen=True)
class TaskStatusChangedEvent(DomainEvent):
    """Event emitted when a Task status changes (formerly SubtaskStatusChangedEvent).

    This event signals that a task has transitioned to a new status.
    """

    task_id: TaskId
    status: TaskStatus | None

    def __post_init__(self) -> None:
        """Initialize event_type for frozen dataclass."""
        object.__setattr__(self, 'event_type', EventType.TASK_STATUS_CHANGED)

