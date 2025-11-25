"""Unit tests for shared core value objects."""

from __future__ import annotations

import pytest

from domain.value_objects.content.dependency_reason import DependencyReason
from domain.value_objects.content.title import Title
from domain.value_objects.identifiers.plan_id import PlanId
from domain.value_objects.identifiers.story_id import StoryId
from domain.value_objects.identifiers.task_id import TaskId


def test_plan_id_rejects_blank() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        PlanId(" ")


def test_plan_id_str_returns_value() -> None:
    assert str(PlanId("plan-001")) == "plan-001"


def test_story_id_rejects_whitespace() -> None:
    with pytest.raises(ValueError, match="cannot be whitespace"):
        StoryId("   ")


def test_story_id_rejects_empty() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        StoryId("")


def test_task_id_rejects_blank() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        TaskId("")


def test_title_rejects_long_value() -> None:
    long_title = "x" * 201
    with pytest.raises(ValueError, match="too long"):
        Title(long_title)


def test_title_rejects_empty() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        Title("")


def test_dependency_reason_rejects_blank() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        DependencyReason("")

