"""Mapper for TaskPlan entity - Infrastructure layer."""

from typing import Any

from core.context.domain.entity_ids.task_id import TaskId
from core.context.domain.task_plan import TaskPlan
from core.context.domain.task_type import TaskType


class TaskPlanMapper:
    """Mapper for TaskPlan conversions (formerly SubtaskPlanDTO)."""

    @staticmethod
    def from_redis_data(data: dict[str, Any]) -> TaskPlan:
        """Create TaskPlan from Redis/Valkey data.

        Args:
            data: Dictionary from Redis with task plan

        Returns:
            TaskPlan domain entity

        Raises:
            KeyError: If required fields are missing
            ValueError: If data is invalid
        """
        # Convert dependency strings to TaskId value objects
        depends_on_ids = [
            TaskId(value=dep_id)
            for dep_id in data.get("depends_on", [])
        ]

        # Parse type string to TaskType enum (fail-fast if invalid)
        type_str = data.get("type", "development")
        try:
            task_type = TaskType(type_str)
        except ValueError as e:
            raise ValueError(
                f"Invalid task type '{type_str}'. "
                f"Must be one of: {[t.value for t in TaskType]}"
            ) from e

        return TaskPlan(
            task_id=TaskId(value=data["task_id"]),
            title=data["title"],
            description=data["description"],
            role=data["role"],
            type=task_type,
            suggested_tech=tuple(data.get("suggested_tech", [])),
            depends_on=tuple(depends_on_ids),
            estimate_points=float(data.get("estimate_points", 0.0)),
            priority=int(data.get("priority", 0)),
            risk_score=float(data.get("risk_score", 0.0)),
            notes=data.get("notes", ""),
        )

    @staticmethod
    def to_dict(task_plan: TaskPlan) -> dict[str, Any]:
        """Convert TaskPlan to dictionary representation.

        Args:
            task_plan: TaskPlan domain entity

        Returns:
            Dictionary with primitive types
        """
        return {
            "task_id": task_plan.task_id.to_string(),
            "title": task_plan.title,
            "description": task_plan.description,
            "role": task_plan.role,
            "type": task_plan.type.value,
            "depends_on": task_plan.get_dependency_ids(),
            "estimate_points": task_plan.estimate_points,
            "priority": task_plan.priority,
            "risk_score": task_plan.risk_score,
            "suggested_tech": list(task_plan.suggested_tech),
            "notes": task_plan.notes,
        }

