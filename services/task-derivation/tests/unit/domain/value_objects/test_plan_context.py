"""Tests for PlanContext value object."""

from __future__ import annotations

import pytest

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


def _valid_plan_context() -> PlanContext:
    return PlanContext(
        plan_id=PlanId("plan-1"),
        story_id=StoryId("story-1"),
        title=Title("Implement auth"),
        description=PlanDescription("Detailed description"),
        acceptance_criteria=AcceptanceCriteria.from_iterable(("AC1",)),
        technical_notes=TechnicalNotes("Not specified"),
        roles=(ContextRole("DEVELOPER"),),
    )


def test_plan_context_accepts_valid_payload() -> None:
    context = _valid_plan_context()
    assert context.title.value == "Implement auth"


def test_plan_context_requires_roles() -> None:
    kwargs = _valid_plan_context().__dict__ | {"roles": ()}
    with pytest.raises(ValueError, match="roles cannot be empty"):
        PlanContext(**kwargs)  # type: ignore[arg-type]

