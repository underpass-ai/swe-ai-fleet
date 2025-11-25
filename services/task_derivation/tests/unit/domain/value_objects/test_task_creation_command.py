"""Tests for TaskCreationCommand value object."""

from __future__ import annotations

import pytest
from core.shared.domain.value_objects.content.task_description import TaskDescription
from core.shared.domain.value_objects.task_attributes.duration import Duration
from core.shared.domain.value_objects.task_attributes.priority import Priority

from task_derivation.domain.value_objects.content.title import Title
from task_derivation.domain.value_objects.identifiers.plan_id import PlanId
from task_derivation.domain.value_objects.identifiers.story_id import StoryId
from task_derivation.domain.value_objects.task_derivation.commands.task_creation_command import (
    TaskCreationCommand,
)
from task_derivation.domain.value_objects.task_derivation.context.context_role import (
    ContextRole,
)


def _valid_command() -> TaskCreationCommand:
    return TaskCreationCommand(
        plan_id=PlanId("plan-1"),
        story_id=StoryId("story-1"),
        title=Title("Implement auth"),
        description=TaskDescription("Do something"),
        estimated_hours=Duration(4),
        priority=Priority(1),
        assigned_role=ContextRole("DEVELOPER"),
    )


def test_task_creation_command_accepts_valid_payload() -> None:
    command = _valid_command()
    assert str(command.assigned_role) == "DEVELOPER"


def test_task_creation_command_rejects_blank_role() -> None:
    with pytest.raises(ValueError, match="ContextRole cannot be empty"):
        ContextRole(" ")

