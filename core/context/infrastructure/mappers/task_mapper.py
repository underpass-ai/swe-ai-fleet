"""Mapper for Task entity - Infrastructure layer."""

from typing import Any

from core.context.domain.entity_ids.plan_id import PlanId
from core.context.domain.entity_ids.task_id import TaskId
from core.context.domain.task import Task
from core.context.domain.task_status import TaskStatus
from core.context.domain.task_type import TaskType


class TaskMapper:
    """Mapper for Task entity conversions (formerly Subtask)."""

    @staticmethod
    def from_event_payload(payload: dict[str, Any]) -> Task:
        """Create Task from event payload.

        Args:
            payload: Event data with {plan_id, task_id, title?, type?, status?}

        Returns:
            Task domain entity

        Raises:
            KeyError: If required fields are missing
            ValueError: If data is invalid
        """
        # Parse type if present
        task_type = TaskType.DEVELOPMENT
        if "type" in payload and payload["type"]:
            type_str = payload["type"]
            if isinstance(type_str, TaskType):
                task_type = type_str
            elif type_str in TaskType.__members__.values():
                task_type = TaskType(type_str)

        # Parse status if present
        status = None
        if "status" in payload and payload["status"]:
            status_str = payload["status"]
            if isinstance(status_str, TaskStatus):
                status = status_str
            elif status_str in TaskStatus.__members__.values():
                status = TaskStatus(status_str)

        return Task(
            plan_id=PlanId(value=payload["plan_id"]),
            task_id=TaskId(value=payload["task_id"]),
            title=payload.get("title", ""),
            type=task_type,
            status=status,
        )

    @staticmethod
    def from_status_update_payload(payload: dict[str, Any]) -> Task:
        """Create Task from status update event.

        Args:
            payload: Event data with {task_id, status, plan_id?}

        Returns:
            Task domain entity with updated status

        Raises:
            KeyError: If required fields are missing
        """
        # Parse status
        status = None
        if "status" in payload and payload["status"]:
            status_str = payload["status"]
            if isinstance(status_str, TaskStatus):
                status = status_str
            elif status_str in TaskStatus.__members__.values():
                status = TaskStatus(status_str)

        # Plan ID is optional in status updates (might need to query from graph)
        plan_id_str = payload.get("plan_id", "unknown")

        return Task(
            plan_id=PlanId(value=plan_id_str),
            task_id=TaskId(value=payload["task_id"]),
            title="",
            type=TaskType.DEVELOPMENT,
            status=status,
        )

    @staticmethod
    def to_dict(task: Task) -> dict[str, Any]:
        """Convert Task to dictionary representation.

        Args:
            task: Task domain entity

        Returns:
            Dictionary with primitive types
        """
        result = {
            "plan_id": task.plan_id.to_string(),
            "task_id": task.task_id.to_string(),
            "title": task.title,
            "type": task.type.value,
        }

        if task.status is not None:
            result["status"] = task.status.value

        return result

