"""Tests for ContextRole value object."""

from __future__ import annotations

import pytest
from task_derivation.domain.value_objects.task_derivation.context.context_role import (
    ContextRole,
)


def test_context_role_accepts_valid_value() -> None:
    role = ContextRole("DEVELOPER")
    assert str(role) == "DEVELOPER"


def test_context_role_rejects_blank_value() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        ContextRole(" ")

