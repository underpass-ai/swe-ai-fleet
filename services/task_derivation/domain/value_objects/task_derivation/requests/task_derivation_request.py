"""TaskDerivationRequest value object."""

from __future__ import annotations

from dataclasses import dataclass

from task_derivation.domain.value_objects.identifiers.plan_id import PlanId
from task_derivation.domain.value_objects.identifiers.story_id import StoryId
from task_derivation.domain.value_objects.task_derivation.context.context_role import (
    ContextRole,
)


@dataclass(frozen=True)
class TaskDerivationRequest:
    """Immutable representation of a task derivation request."""

    plan_id: PlanId
    story_id: StoryId
    roles: tuple[ContextRole, ...]
    requested_by: str

    def __post_init__(self) -> None:
        if not self.roles:
            raise ValueError("roles cannot be empty for task derivation request")
        if not self.requested_by or not self.requested_by.strip():
            raise ValueError("requested_by cannot be empty")

