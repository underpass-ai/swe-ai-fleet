"""Unit tests for TaskNode value object."""

from __future__ import annotations

import pytest

from core.shared.domain.value_objects.content.task_description import TaskDescription
from task_derivation.domain.value_objects.content.title import Title
from task_derivation.domain.value_objects.identifiers.task_id import TaskId
from core.shared.domain.value_objects.task_attributes.duration import Duration
from core.shared.domain.value_objects.task_attributes.priority import Priority
from core.shared.domain.value_objects.task_derivation.keyword import (
    Keyword,
)
from task_derivation.domain.value_objects.task_derivation.dependency.task_node import (
    TaskNode,
)


class TestTaskNode:
    """Tests for TaskNode invariants and behavior."""

    def _build_task_node(self, keywords: tuple[Keyword, ...] | list[Keyword]) -> TaskNode:
        return TaskNode(
            task_id=TaskId("TASK-001"),
            title=Title("Implement API"),
            description=TaskDescription("Build the HTTP API."),
            keywords=keywords,  # type: ignore[arg-type]
            estimated_hours=Duration(8),
            priority=Priority(1),
        )

    def test_keywords_must_be_tuple(self) -> None:
        """Fail fast when keywords is not a tuple."""
        with pytest.raises(ValueError, match="keywords must be a tuple"):
            self._build_task_node([Keyword("api")])

    def test_has_keyword_matching_detects_keyword(self) -> None:
        """Verify keyword matching delegates to Keyword VO."""
        node = self._build_task_node((Keyword("database"),))

        assert node.has_keyword_matching("Database schema ready")
        assert not node.has_keyword_matching("no match")

