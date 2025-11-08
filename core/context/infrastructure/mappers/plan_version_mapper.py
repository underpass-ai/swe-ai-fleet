"""Mapper for PlanVersion entity - Infrastructure layer."""

from typing import Any

from core.context.domain.entity_ids.actor_id import ActorId
from core.context.domain.entity_ids.plan_id import PlanId
from core.context.domain.entity_ids.story_id import StoryId
from core.context.domain.plan_version import PlanVersion
from core.context.domain.task_plan import TaskPlan
from core.context.infrastructure.mappers.task_plan_mapper import TaskPlanMapper


class PlanVersionMapper:
    """Mapper for PlanVersion entity conversions."""

    @staticmethod
    def from_redis_data(data: dict[str, Any]) -> PlanVersion:
        """Create PlanVersion from Redis/Valkey data.

        Args:
            data: Dictionary from Redis with plan version data

        Returns:
            PlanVersion domain entity

        Raises:
            KeyError: If required fields are missing
            ValueError: If data is invalid
        """
        # Parse tasks (formerly subtasks)
        tasks: list[TaskPlan] = []
        for task_data in data.get("subtasks", []):  # Legacy key name
            tasks.append(TaskPlanMapper.from_redis_data(task_data))

        # Parse author_id (optional)
        author_id_str = data.get("author_id")
        author_id = ActorId(value=author_id_str) if author_id_str else None

        return PlanVersion(
            plan_id=PlanId(value=data["plan_id"]),
            version=int(data.get("version", 1)),
            story_id=StoryId(value=data.get("case_id", data.get("story_id", ""))),  # Support both legacy and new
            status=data.get("status", "draft"),
            author_id=author_id,
            rationale=data.get("rationale", ""),
            tasks=tuple(tasks),  # Immutable tuple
            created_at_ms=int(data.get("created_at_ms", 0)),
        )

    @staticmethod
    def from_event_payload(payload: dict[str, Any]) -> PlanVersion:
        """Create a PlanVersion from event payload data.

        Args:
            payload: Event payload dict with plan_id, story_id, and optional version

        Returns:
            PlanVersion domain entity

        Raises:
            KeyError: If required fields are missing
            ValueError: If IDs are invalid or version < 1
        """
        return PlanVersion(
            plan_id=PlanId(value=payload["plan_id"]),
            version=int(payload.get("version", 1)),
            story_id=StoryId(value=payload["story_id"]),
        )

    @staticmethod
    def to_graph_properties(plan: PlanVersion) -> dict[str, Any]:
        """Convert PlanVersion to properties suitable for Neo4j graph storage.

        Args:
            plan: PlanVersion domain entity

        Returns:
            Dictionary with properties for Neo4j
        """
        return {
            "plan_id": plan.plan_id.to_string(),
            "version": plan.version,
            "story_id": plan.story_id.to_string(),
        }

