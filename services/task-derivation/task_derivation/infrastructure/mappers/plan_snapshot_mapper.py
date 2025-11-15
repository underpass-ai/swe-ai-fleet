"""Mapper between Planning payloads, DTOs, and domain objects."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from task_derivation.domain.value_objects.content import (
    AcceptanceCriteria,
    PlanDescription,
    TechnicalNotes,
    Title,
)
from task_derivation.domain.value_objects.identifiers.plan_id import PlanId
from task_derivation.domain.value_objects.identifiers.story_id import StoryId
from task_derivation.domain.value_objects.task_derivation.context.context_role import (
    ContextRole,
)
from task_derivation.domain.value_objects.task_derivation.context.plan_context import (
    PlanContext,
)
from task_derivation.infrastructure.dto.plan_snapshot_dto import PlanSnapshotDTO


class PlanSnapshotMapper:
    """Utility for converting Planning payloads into domain objects."""

    @staticmethod
    def from_planning_payload(payload: Mapping[str, Any]) -> PlanSnapshotDTO:
        """Build DTO from raw mapping returned by gRPC/HTTP clients."""
        acceptance_criteria = tuple(PlanSnapshotMapper._ensure_sequence(payload.get("acceptance_criteria")))
        roles = tuple(PlanSnapshotMapper._ensure_sequence(payload.get("roles")))

        return PlanSnapshotDTO(
            plan_id=str(payload["plan_id"]),
            story_id=str(payload["story_id"]),
            title=str(payload["title"]),
            description=str(payload["description"]),
            acceptance_criteria=acceptance_criteria,
            technical_notes=str(payload.get("technical_notes", "Not specified")),
            roles=roles or ("developer",),
        )

    @staticmethod
    def to_plan_context(dto: PlanSnapshotDTO) -> PlanContext:
        """Convert infrastructure DTO into domain PlanContext VO."""
        return PlanContext(
            plan_id=PlanId(dto.plan_id),
            story_id=StoryId(dto.story_id),
            title=Title(dto.title),
            description=PlanDescription(dto.description),
            acceptance_criteria=AcceptanceCriteria.from_iterable(dto.acceptance_criteria),
            technical_notes=TechnicalNotes(dto.technical_notes),
            roles=tuple(ContextRole(role) for role in dto.roles),
        )

    @staticmethod
    def _ensure_sequence(value: Any) -> Sequence[str]:
        """Normalize acceptance criteria / roles to sequences."""
        if value is None:
            return ()
        if isinstance(value, (list, tuple)):
            return tuple(str(item) for item in value)
        return (str(value),)

