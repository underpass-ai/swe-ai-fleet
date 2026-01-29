"""Unified mapper from Planning NATS events to Domain Entities.

Anti-Corruption Layer (ACL) that translates Planning BC events to Context BC entities.

This mapper combines:
1. JSON payload → DTO (internal, not exposed)
2. DTO → Domain Entity (internal, not exposed)

Consumers only see: JSON → Entity (single call)
"""

from typing import Any

from core.context.infrastructure.dtos.story_created_dto import StoryCreatedDTO
from core.context.domain.entity_ids.epic_id import EpicId
from core.context.domain.entity_ids.plan_id import PlanId
from core.context.domain.entity_ids.project_id import ProjectId
from core.context.domain.entity_ids.story_id import StoryId
from core.context.domain.entity_ids.task_id import TaskId
from core.context.domain.epic import Epic
from core.context.domain.epic_status import EpicStatus
from core.context.domain.phase_transition import PhaseTransition
from core.context.domain.plan_approval import PlanApproval
from core.context.domain.project import Project
from core.context.domain.project_status import ProjectStatus
from core.context.domain.story import Story
from core.context.domain.task import Task
from core.context.domain.task_status import TaskStatus
from core.context.domain.task_type import TaskType


class PlanningEventMapper:
    """Unified mapper for Planning events → Domain entities.

    Handles TWO types of Planning events:
    1. NATS events from Planning Service (payload_to_* methods)
    2. Redis/Valkey stored events (from_redis_data method)

    Anti-Corruption Layer that protects Context BC from Planning BC changes.

    Responsibilities:
    - Parse JSON payloads (NATS)
    - Parse Redis data structures
    - Handle missing/optional fields
    - Convert to domain entities
    - Domain validation (via entity __post_init__)
    """

    @staticmethod
    def from_redis_data(data: dict[str, Any]):
        """Create PlanningEvent from Redis/Valkey data.

        Args:
            data: Dictionary from Redis with event data

        Returns:
            PlanningEvent domain entity (dict-based, legacy format)

        Raises:
            KeyError: If required fields are missing

        Note: This returns a dict-based event (legacy format).
        TODO: Migrate to proper domain entity when PlanningEvent class is refactored.
        """
        from core.context.domain.entity_ids.actor_id import ActorId
        from core.context.domain.planning_event import PlanningEvent

        return PlanningEvent(
            id=data["id"],
            event=data["event"],
            actor_id=ActorId(value=data["actor"]),
            payload=dict(data.get("payload", {})),
            ts_ms=int(data.get("ts_ms", 0)),
        )

    @staticmethod
    def payload_to_project(payload: dict[str, Any]) -> Project:
        """Convert planning.project.created payload to Project entity.

        Args:
            payload: JSON dict from NATS message

        Returns:
            Project domain entity

        Raises:
            KeyError: If required fields missing
            ValueError: If domain validation fails
        """
        return Project(
            project_id=ProjectId(value=payload["project_id"]),
            name=payload["name"],
            description=payload.get("description", ""),
            status=ProjectStatus(payload.get("status", "active")),
            owner=payload.get("owner", ""),
            created_at_ms=int(payload.get("created_at_ms", 0)),
        )

    @staticmethod
    def payload_to_epic(payload: dict[str, Any]) -> Epic:
        """Convert planning.epic.created payload to Epic entity."""
        return Epic(
            epic_id=EpicId(value=payload["epic_id"]),
            project_id=ProjectId(value=payload["project_id"]),
            title=payload["title"],
            description=payload.get("description", ""),
            status=EpicStatus(payload.get("status", "active")),
            created_at_ms=int(payload.get("created_at_ms", 0)),
        )

    @staticmethod
    def _payload_to_story_created_dto(payload: dict[str, Any]) -> StoryCreatedDTO:
        """Validate raw payload and build typed StoryCreatedDTO.

        Required payload keys: story_id, epic_id; and either name or title (all must be str).
        Planning BC sends 'title'; Context BC uses 'name'. Both accepted.

        Raises:
            ValueError: If required fields are missing or not str (fail-fast).
        """
        if "story_id" not in payload:
            raise ValueError(
                "Missing required field 'story_id' in story.created payload. "
                "Domain Invariant: Story must have a unique identifier."
            )
        if "epic_id" not in payload:
            raise ValueError(
                "Missing required field 'epic_id' in story.created payload. "
                "Domain Invariant: Story MUST belong to an Epic. No orphan stories allowed."
            )
        story_id_val = payload["story_id"]
        epic_id_val = payload["epic_id"]
        name_or_title = payload.get("name") or payload.get("title")
        if name_or_title is None:
            raise ValueError(
                "Missing required field 'name' or 'title' in story.created payload. "
                "Story display name is required."
            )
        if not isinstance(story_id_val, str):
            raise ValueError(
                f"Field 'story_id' in story.created payload must be str, got {type(story_id_val).__name__}."
            )
        if not isinstance(epic_id_val, str):
            raise ValueError(
                f"Field 'epic_id' in story.created payload must be str, got {type(epic_id_val).__name__}."
            )
        if not isinstance(name_or_title, str):
            raise ValueError(
                f"Field 'name' or 'title' in story.created payload must be str, got {type(name_or_title).__name__}."
            )
        name = name_or_title.strip()
        if not name:
            raise ValueError(
                "Field 'name' or 'title' in story.created payload cannot be empty or whitespace."
            )
        return StoryCreatedDTO(story_id=story_id_val, epic_id=epic_id_val, name=name)

    @staticmethod
    def payload_to_story(payload: dict[str, Any]) -> Story:
        """Convert planning.story.created payload to Story entity.

        Required payload keys: story_id, epic_id, and either name or title (all str).
        Planning BC sends 'title'; Context BC Story uses 'name'. Both accepted.

        Raises:
            ValueError: If required fields are missing or not str (fail-fast, no KeyError).
        """
        dto = PlanningEventMapper._payload_to_story_created_dto(payload)
        return Story(
            story_id=StoryId(value=dto.story_id),
            epic_id=EpicId(value=dto.epic_id),
            name=dto.name,
        )

    @staticmethod
    def payload_to_task(payload: dict[str, Any]) -> Task:
        """Convert planning.task.created payload to Task entity."""
        return Task(
            task_id=TaskId(value=payload["task_id"]),
            plan_id=PlanId(value=payload["plan_id"]),
            title=payload["title"],
            type=TaskType(payload.get("type", "development")),
            status=TaskStatus(payload.get("status", "todo")),
        )

    @staticmethod
    def payload_to_plan_approval(payload: dict[str, Any]) -> PlanApproval:
        """Convert planning.plan.approved payload to PlanApproval entity.

        Required: plan_id, story_id, approved_by; and either timestamp or approved_at (str).
        Planning BC sends 'approved_at'; Context BC PlanApproval uses 'timestamp'. Both accepted.

        Raises:
            ValueError: If required fields are missing or not str (fail-fast).
        """
        for key in ("plan_id", "story_id", "approved_by"):
            if key not in payload:
                raise ValueError(
                    f"Missing required field '{key}' in plan.approved payload."
                )
        ts_val = payload.get("timestamp") or payload.get("approved_at")
        if ts_val is None:
            raise ValueError(
                "Missing required field 'timestamp' or 'approved_at' in plan.approved payload."
            )
        plan_id_val = payload["plan_id"]
        story_id_val = payload["story_id"]
        approved_by_val = payload["approved_by"]
        if not isinstance(plan_id_val, str):
            raise ValueError(
                f"Field 'plan_id' in plan.approved payload must be str, got {type(plan_id_val).__name__}."
            )
        if not isinstance(story_id_val, str):
            raise ValueError(
                f"Field 'story_id' in plan.approved payload must be str, got {type(story_id_val).__name__}."
            )
        if not isinstance(approved_by_val, str):
            raise ValueError(
                f"Field 'approved_by' in plan.approved payload must be str, got {type(approved_by_val).__name__}."
            )
        if not isinstance(ts_val, str):
            raise ValueError(
                f"Field 'timestamp' or 'approved_at' in plan.approved payload must be str, got {type(ts_val).__name__}."
            )
        ts = ts_val.strip()
        if not ts:
            raise ValueError(
                "Field 'timestamp' or 'approved_at' in plan.approved payload cannot be empty."
            )
        return PlanApproval(
            plan_id=PlanId(value=plan_id_val),
            story_id=StoryId(value=story_id_val),
            approved_by=approved_by_val.strip(),
            timestamp=ts,
        )

    @staticmethod
    def payload_to_phase_transition(payload: dict[str, Any]) -> PhaseTransition:
        """Convert planning.story.transitioned payload to PhaseTransition entity."""
        return PhaseTransition(
            story_id=StoryId(value=payload["story_id"]),
            from_phase=payload["from_phase"],
            to_phase=payload["to_phase"],
            timestamp=payload["timestamp"],
        )
