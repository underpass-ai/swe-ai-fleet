"""Mapper for task.derivation.requested payloads."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from task_derivation.domain.value_objects.identifiers.plan_id import PlanId
from task_derivation.domain.value_objects.identifiers.story_id import StoryId
from task_derivation.domain.value_objects.task_derivation.context.context_role import (
    ContextRole,
)
from task_derivation.domain.value_objects.task_derivation.requests.task_derivation_request import (
    TaskDerivationRequest,
)


@dataclass(frozen=True)
class TaskDerivationRequestDTO:
    """Infrastructure DTO for task.derivation.requested events."""

    plan_id: str
    story_id: str
    roles: tuple[str, ...]
    requested_by: str

    def __post_init__(self) -> None:
        if not self.plan_id or not self.plan_id.strip():
            raise ValueError("plan_id is required in derivation request")
        if not self.story_id or not self.story_id.strip():
            raise ValueError("story_id is required in derivation request")
        if not self.roles:
            raise ValueError("roles cannot be empty in derivation request")
        if not self.requested_by or not self.requested_by.strip():
            raise ValueError("requested_by cannot be empty in derivation request")


class TaskDerivationRequestMapper:
    """Convert raw event payloads into domain requests."""

    DEFAULT_ROLE = "DEVELOPER"

    @staticmethod
    def from_event(payload: Mapping[str, Any]) -> TaskDerivationRequest:
        dto = TaskDerivationRequestDTO(
            plan_id=str(payload.get("plan_id", "")).strip(),
            story_id=str(payload.get("story_id", "")).strip(),
            roles=TaskDerivationRequestMapper._normalize_roles(payload.get("roles")),
            requested_by=str(payload.get("requested_by", "")).strip(),
        )

        roles = tuple(ContextRole(role) for role in dto.roles)

        return TaskDerivationRequest(
            plan_id=PlanId(dto.plan_id),
            story_id=StoryId(dto.story_id),
            roles=roles,
            requested_by=dto.requested_by,
        )

    @staticmethod
    def _normalize_roles(raw_roles: Any) -> tuple[str, ...]:
        if raw_roles is None:
            return (TaskDerivationRequestMapper.DEFAULT_ROLE,)

        if isinstance(raw_roles, str):
            cleaned = raw_roles.strip()
            return (cleaned or TaskDerivationRequestMapper.DEFAULT_ROLE,)

        if isinstance(raw_roles, Sequence):
            roles = tuple(role.strip() for role in raw_roles if str(role).strip())
            if roles:
                return roles

        return (TaskDerivationRequestMapper.DEFAULT_ROLE,)

