"""Unit tests for Guard value object."""

import pytest

from core.ceremony_engine.domain.value_objects.guard import Guard
from core.ceremony_engine.domain.value_objects.guard_type import GuardType


def test_guard_automated_happy_path() -> None:
    """Test creating a valid automated guard."""
    guard = Guard(
        name="selection_valid",
        type=GuardType.AUTOMATED,
        check="scored_stories.length >= 1",
    )

    assert guard.name == "selection_valid"
    assert guard.type == GuardType.AUTOMATED
    assert guard.check == "scored_stories.length >= 1"
    assert guard.role is None
    assert guard.threshold is None


def test_guard_human_happy_path() -> None:
    """Test creating a valid human guard."""
    guard = Guard(
        name="po_approved",
        type=GuardType.HUMAN,
        check="PO has explicitly approved",
        role="PO",
    )

    assert guard.name == "po_approved"
    assert guard.type == GuardType.HUMAN
    assert guard.check == "PO has explicitly approved"
    assert guard.role == "PO"


def test_guard_with_threshold() -> None:
    """Test creating a guard with threshold."""
    guard = Guard(
        name="score_threshold",
        type=GuardType.AUTOMATED,
        check="score >= threshold",
        threshold=75.0,
    )

    assert guard.threshold == 75.0


def test_guard_rejects_empty_name() -> None:
    """Test that empty name raises ValueError."""
    with pytest.raises(ValueError, match="Guard name cannot be empty"):
        Guard(name="", type=GuardType.AUTOMATED, check="expression")


def test_guard_rejects_whitespace_name() -> None:
    """Test that whitespace-only name raises ValueError."""
    with pytest.raises(ValueError, match="Guard name cannot be empty"):
        Guard(name="   ", type=GuardType.AUTOMATED, check="expression")


def test_guard_rejects_empty_check() -> None:
    """Test that empty check raises ValueError."""
    with pytest.raises(ValueError, match="Guard check cannot be empty"):
        Guard(name="guard_name", type=GuardType.AUTOMATED, check="")


def test_guard_rejects_whitespace_check() -> None:
    """Test that whitespace-only check raises ValueError."""
    with pytest.raises(ValueError, match="Guard check cannot be empty"):
        Guard(name="guard_name", type=GuardType.AUTOMATED, check="   ")


def test_guard_is_immutable() -> None:
    """Test that guard is immutable (frozen dataclass)."""
    guard = Guard(name="test", type=GuardType.AUTOMATED, check="expression")

    with pytest.raises(Exception):  # frozen dataclass raises exception on mutation
        guard.name = "changed"  # type: ignore[misc]
