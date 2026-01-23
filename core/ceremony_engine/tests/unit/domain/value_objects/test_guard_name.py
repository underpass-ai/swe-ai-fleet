"""Unit tests for GuardName value object."""

import pytest

from core.ceremony_engine.domain.value_objects.guard_name import GuardName


def test_guard_name_happy_path() -> None:
    """Test creating a valid GuardName."""
    name = GuardName("human_approval")

    assert name.value == "human_approval"


def test_guard_name_rejects_empty_value() -> None:
    """Test that empty value raises ValueError."""
    with pytest.raises(ValueError, match="GuardName value cannot be empty"):
        GuardName("")


def test_guard_name_rejects_whitespace_value() -> None:
    """Test that whitespace-only value raises ValueError."""
    with pytest.raises(ValueError, match="GuardName value cannot be empty"):
        GuardName("   ")
