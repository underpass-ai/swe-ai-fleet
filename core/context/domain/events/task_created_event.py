"""TaskCreatedEvent - Domain event for task creation."""

from dataclasses import dataclass

from core.context.domain.domain_event import DomainEvent
from core.context.domain.entity_ids.plan_id import PlanId
from core.context.domain.entity_ids.task_id import TaskId
from core.context.domain.event_type import EventType
from core.context.domain.task_type import TaskType


@dataclass(frozen=True)
class TaskCreatedEvent(DomainEvent):
    """Event emitted when a Task is created (formerly SubtaskCreatedEvent).

    This event signals that a new task has been created within a plan.
    """

    plan_id: PlanId
    task_id: TaskId
    title: str
    type: TaskType
    event_type: EventType = EventType.TASK_CREATED
