"""Tests for TaskSummary value object."""

from __future__ import annotations

import pytest

from task_derivation.domain.value_objects.content.title import Title
from task_derivation.domain.value_objects.identifiers.task_id import TaskId
from task_derivation.domain.value_objects.task_attributes.priority import Priority
from task_derivation.domain.value_objects.task_derivation.context.context_role import (
    ContextRole,
)
from task_derivation.domain.value_objects.task_derivation.summary.task_summary import (
    TaskSummary,
)


def test_task_summary_accepts_valid_payload() -> None:
    summary = TaskSummary(
        task_id=TaskId("task-1"),
        title=Title("Existing"),
        priority=Priority(1),
        assigned_role=ContextRole("DEVELOPER"),
    )

    assert str(summary.assigned_role) == "DEVELOPER"


def test_task_summary_rejects_blank_role() -> None:
    with pytest.raises(ValueError, match="ContextRole cannot be empty"):
        ContextRole(" ")

