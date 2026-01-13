"""Unit tests for Timeouts value object."""

import pytest

from core.ceremony_engine.domain.value_objects.timeouts import Timeouts


def test_timeouts_happy_path() -> None:
    """Test creating valid timeouts."""
    timeouts = Timeouts(step_default=60, step_max=3600, ceremony_max=86400)

    assert timeouts.step_default == 60
    assert timeouts.step_max == 3600
    assert timeouts.ceremony_max == 86400


def test_timeouts_allows_equal_default_and_max() -> None:
    """Test that step_default can equal step_max."""
    timeouts = Timeouts(step_default=60, step_max=60, ceremony_max=86400)
    assert timeouts.step_default == timeouts.step_max


def test_timeouts_rejects_step_default_zero() -> None:
    """Test that step_default <= 0 raises ValueError."""
    with pytest.raises(ValueError, match="step_default must be > 0"):
        Timeouts(step_default=0, step_max=3600, ceremony_max=86400)


def test_timeouts_rejects_step_default_negative() -> None:
    """Test that negative step_default raises ValueError."""
    with pytest.raises(ValueError, match="step_default must be > 0"):
        Timeouts(step_default=-1, step_max=3600, ceremony_max=86400)


def test_timeouts_rejects_step_max_zero() -> None:
    """Test that step_max <= 0 raises ValueError."""
    with pytest.raises(ValueError, match="step_max must be > 0"):
        Timeouts(step_default=60, step_max=0, ceremony_max=86400)


def test_timeouts_rejects_ceremony_max_zero() -> None:
    """Test that ceremony_max <= 0 raises ValueError."""
    with pytest.raises(ValueError, match="ceremony_max must be > 0"):
        Timeouts(step_default=60, step_max=3600, ceremony_max=0)


def test_timeouts_rejects_default_greater_than_max() -> None:
    """Test that step_default > step_max raises ValueError."""
    with pytest.raises(ValueError, match="step_default.*must be <= step_max"):
        Timeouts(step_default=3600, step_max=60, ceremony_max=86400)


def test_timeouts_is_immutable() -> None:
    """Test that timeouts is immutable (frozen dataclass)."""
    timeouts = Timeouts(step_default=60, step_max=3600, ceremony_max=86400)

    with pytest.raises(Exception):  # frozen dataclass raises exception on mutation
        timeouts.step_default = 120  # type: ignore[misc]
