"""Unit tests for shared core value objects."""

from __future__ import annotations

import pytest

from task_derivation.domain.value_objects.content.dependency_reason import (
    DependencyReason,
)
from task_derivation.domain.value_objects.content.task_description import (
    TaskDescription,
)
from task_derivation.domain.value_objects.content.title import Title
from task_derivation.domain.value_objects.identifiers.plan_id import PlanId
from task_derivation.domain.value_objects.identifiers.story_id import StoryId
from task_derivation.domain.value_objects.identifiers.task_id import TaskId
from task_derivation.domain.value_objects.task_derivation.dependency.keyword import (
    Keyword,
)


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


def test_task_description_rejects_long_value() -> None:
    long_description = "x" * 2001
    with pytest.raises(ValueError, match="too long"):
        TaskDescription(long_description)


def test_task_description_rejects_empty() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        TaskDescription("")


def test_dependency_reason_rejects_blank() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        DependencyReason("")


def test_keyword_matching_is_case_insensitive() -> None:
    keyword = Keyword("Graph")

    assert keyword.matches_in("graph database ready")
    assert not keyword.matches_in("")


def test_keyword_rejects_blank_value() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        Keyword("")

