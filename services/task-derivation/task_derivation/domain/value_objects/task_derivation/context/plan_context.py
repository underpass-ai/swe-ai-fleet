"""PlanContext value object used by derivation domain logic."""

from dataclasses import dataclass

from task_derivation.domain.value_objects.content.plan_description import PlanDescription
from task_derivation.domain.value_objects.content.acceptance_criteria import (
    AcceptanceCriteria,
)
from task_derivation.domain.value_objects.content.technical_notes import TechnicalNotes
from task_derivation.domain.value_objects.content.title import Title
from task_derivation.domain.value_objects.identifiers.plan_id import PlanId
from task_derivation.domain.value_objects.identifiers.story_id import StoryId
from task_derivation.domain.value_objects.task_derivation.context.context_role import (
    ContextRole,
)


@dataclass(frozen=True)
class PlanContext:
    """Immutable snapshot of a plan ready for derivation."""

    plan_id: PlanId
    story_id: StoryId
    title: Title
    description: PlanDescription
    acceptance_criteria: AcceptanceCriteria
    technical_notes: TechnicalNotes
    roles: tuple[ContextRole, ...]

    def __post_init__(self) -> None:
        """Validate payload."""
        if not self.roles:
            raise ValueError("PlanContext.roles cannot be empty")

