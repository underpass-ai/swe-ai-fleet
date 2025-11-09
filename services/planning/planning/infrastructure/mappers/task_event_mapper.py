"""TaskEventMapper - Infrastructure layer mapper for Task events."""

from typing import Any

from planning.domain.entities.task import Task
from planning.domain.events.task_created_event import TaskCreatedEvent


class TaskEventMapper:
    """Mapper for Task domain events to dict/JSON.

    Following Hexagonal Architecture:
    - Mappers live in infrastructure layer
    - Handle conversions: DomainEvent → dict (for NATS/JSON)
    - Domain entities → Events happen in use cases
    """

    @staticmethod
    def task_to_created_event(task: Task) -> TaskCreatedEvent:
        """Convert Task entity to TaskCreatedEvent.

        Args:
            task: Task domain entity

        Returns:
            TaskCreatedEvent (domain event)
        """
        return TaskCreatedEvent(
            task_id=task.task_id,
            plan_id=task.plan_id,
            story_id=task.story_id,
            title=task.title,
            description=task.description,
            type=task.type,
            assigned_to=task.assigned_to,
            estimated_hours=task.estimated_hours,
            priority=task.priority,
            created_at=task.created_at,
        )

    @staticmethod
    def created_event_to_payload(event: TaskCreatedEvent) -> dict[str, Any]:
        """Convert TaskCreatedEvent to event payload dict.

        Args:
            event: TaskCreatedEvent

        Returns:
            Dictionary for NATS/JSON serialization
        """
        return {
            "task_id": str(event.task_id),
            "plan_id": str(event.plan_id),
            "story_id": str(event.story_id),
            "title": event.title,
            "description": event.description,
            "type": str(event.type),
            "assigned_to": event.assigned_to,
            "estimated_hours": event.estimated_hours,
            "priority": event.priority,
            "created_at": event.created_at.isoformat(),
        }

