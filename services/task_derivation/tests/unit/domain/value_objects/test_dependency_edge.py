"""Tests for DependencyEdge value object."""

from __future__ import annotations

import pytest
from task_derivation.domain.value_objects.content.dependency_reason import (
    DependencyReason,
)
from task_derivation.domain.value_objects.identifiers.task_id import TaskId
from task_derivation.domain.value_objects.task_derivation.dependency.dependency_edge import (
    DependencyEdge,
)


def test_dependency_edge_rejects_self_dependency() -> None:
    """Ensure self-dependencies fail fast."""
    with pytest.raises(ValueError, match="self-dependency"):
        DependencyEdge(
            from_task_id=TaskId("TASK-001"),
            to_task_id=TaskId("TASK-001"),
            reason=DependencyReason("invalid"),
        )

