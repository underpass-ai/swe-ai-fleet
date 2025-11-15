"""Mapper for Story domain events to payloads."""

from typing import Any

from planning.domain.events.story_tasks_not_ready_event import StoryTasksNotReadyEvent


class StoryEventMapper:
    """Mapper for Story domain events to external formats.

    Infrastructure Mapper:
    - Converts domain events → external formats (dict/JSON)
    - Anti-corruption layer (domain → external)
    - NO serialization methods in domain events (DDD rule)
    """

    @staticmethod
    def tasks_not_ready_event_to_payload(event: StoryTasksNotReadyEvent) -> dict[str, Any]:
        """Convert StoryTasksNotReadyEvent to payload dict.

        Args:
            event: Domain event

        Returns:
            Payload dict for NATS
        """
        return {
            "story_id": event.story_id.value,
            "reason": event.reason,
            "task_ids_without_priority": [str(task_id) for task_id in event.task_ids_without_priority],
            "total_tasks": event.total_tasks,
            "occurred_at": event.occurred_at.isoformat(),
        }

