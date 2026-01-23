"""Unit tests for StepId value object."""

import pytest

from core.ceremony_engine.domain.value_objects.step_id import StepId


def test_step_id_happy_path() -> None:
    """Test creating a valid StepId."""
    step_id = StepId("process_step")

    assert step_id.value == "process_step"


def test_step_id_rejects_empty_value() -> None:
    """Test that empty value raises ValueError."""
    with pytest.raises(ValueError, match="StepId value cannot be empty"):
        StepId("")


def test_step_id_rejects_whitespace_value() -> None:
    """Test that whitespace-only value raises ValueError."""
    with pytest.raises(ValueError, match="StepId value cannot be empty"):
        StepId("   ")


def test_step_id_rejects_invalid_snake_case() -> None:
    """Test that invalid snake_case raises ValueError."""
    with pytest.raises(ValueError, match="StepId must be snake_case"):
        StepId("Invalid-Step")
