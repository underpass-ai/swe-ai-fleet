"""Mapper for DomainEvent - Infrastructure layer.

Handles construction of DomainEvents from external data and extraction of entity IDs.
"""

from typing import Any

from core.context.domain.decision_kind import DecisionKind
from core.context.domain.domain_event import DomainEvent
from core.context.domain.event_type import EventType
from core.context.domain.task_status import TaskStatus
from core.context.domain.task_type import TaskType


class DomainEventMapper:
    """Mapper for DomainEvent factory methods and extraction."""

    @staticmethod
    def story_created(story_id: str, name: str = "") -> DomainEvent:
        """Create a story.created domain event (formerly case.created).

        Args:
            story_id: Story identifier
            name: Optional story name

        Returns:
            DomainEvent for story creation
        """
        return DomainEvent(
            event_type=EventType.STORY_CREATED,
            payload={"story_id": story_id, "name": name}
        )

    @staticmethod
    def plan_versioned(story_id: str, plan_id: str, version: int = 1) -> DomainEvent:
        """Create a plan.versioned domain event.

        Args:
            story_id: Story identifier (formerly case_id)
            plan_id: Plan identifier
            version: Plan version number

        Returns:
            DomainEvent for plan versioning
        """
        return DomainEvent(
            event_type=EventType.PLAN_VERSIONED,
            payload={"story_id": story_id, "plan_id": plan_id, "version": version}
        )

    @staticmethod
    def task_created(plan_id: str, task_id: str, title: str = "", type: TaskType = TaskType.DEVELOPMENT) -> DomainEvent:
        """Create a task.created domain event (formerly subtask.created).

        Args:
            plan_id: Plan identifier
            task_id: Task identifier (formerly sub_id)
            title: Task title
            type: Task type

        Returns:
            DomainEvent for task creation
        """
        return DomainEvent(
            event_type=EventType.TASK_CREATED,
            payload={"plan_id": plan_id, "task_id": task_id, "title": title, "type": type},
        )

    @staticmethod
    def task_status_changed(task_id: str, status: TaskStatus | None) -> DomainEvent:
        """Create a task.status_changed domain event (formerly subtask.status_changed).

        Args:
            task_id: Task identifier (formerly sub_id)
            status: New status

        Returns:
            DomainEvent for task status change
        """
        return DomainEvent(
            event_type=EventType.TASK_STATUS_CHANGED,
            payload={"task_id": task_id, "status": status}
        )

    @staticmethod
    def decision_made(
        node_id: str,
        kind: DecisionKind = DecisionKind.IMPLEMENTATION,
        summary: str = "",
        task_id: str | None = None
    ) -> DomainEvent:
        """Create a decision.made domain event.

        Args:
            node_id: Decision node identifier
            kind: Decision kind/category
            summary: Decision summary
            task_id: Optional related task ID (formerly sub_id)

        Returns:
            DomainEvent for decision creation
        """
        payload = {"node_id": node_id, "kind": kind, "summary": summary}
        if task_id is not None:
            payload["task_id"] = task_id
        return DomainEvent(event_type=EventType.DECISION_MADE, payload=payload)

    @staticmethod
    def get_entity_id(event: DomainEvent) -> str | None:
        """Extract the primary entity ID from event payload.

        This is infrastructure logic that understands event structure.

        Args:
            event: DomainEvent to extract ID from

        Returns:
            Entity ID string or None if not found
        """
        # Pattern match on event type enum
        if event.event_type == EventType.STORY_CREATED:
            return event.payload.get("story_id")
        elif event.event_type == EventType.PLAN_VERSIONED:
            return event.payload.get("plan_id")
        elif event.event_type == EventType.TASK_CREATED:
            return event.payload.get("task_id")
        elif event.event_type == EventType.TASK_STATUS_CHANGED:
            return event.payload.get("task_id")
        elif event.event_type == EventType.DECISION_MADE:
            return event.payload.get("node_id")

        # Fallback to generic ID fields (support both old and new names for backward compatibility)
        id_fields = ["story_id", "task_id", "plan_id", "node_id", "case_id", "sub_id"]
        for field in id_fields:
            if field in event.payload:
                return event.payload[field]
        return None

    @staticmethod
    def to_dict(event: DomainEvent) -> dict[str, Any]:
        """Convert DomainEvent to dictionary representation.

        Args:
            event: DomainEvent to serialize

        Returns:
            Dictionary representation
        """
        return {
            "event_type": event.event_type,
            "payload": event.payload,
        }

