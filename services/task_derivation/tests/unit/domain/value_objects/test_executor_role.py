"""Tests for ExecutorRole value object."""

from __future__ import annotations

import pytest
from task_derivation.domain.value_objects.task_derivation.roles.executor_role import (
    ExecutorRole,
)


def test_executor_role_accepts_valid_value() -> None:
    role = ExecutorRole("SYSTEM")
    assert str(role) == "SYSTEM"


def test_executor_role_rejects_blank_value() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        ExecutorRole(" ")

