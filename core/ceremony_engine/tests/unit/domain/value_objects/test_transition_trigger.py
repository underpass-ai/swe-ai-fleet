"""Unit tests for TransitionTrigger value object."""

import pytest

from core.ceremony_engine.domain.value_objects.transition_trigger import TransitionTrigger


def test_transition_trigger_happy_path() -> None:
    """Test creating a valid transition trigger."""
    trigger = TransitionTrigger("start_processing")

    assert trigger.value == "start_processing"


def test_transition_trigger_rejects_empty_value() -> None:
    """Test that empty value raises ValueError."""
    with pytest.raises(ValueError, match="TransitionTrigger value cannot be empty"):
        TransitionTrigger("")


def test_transition_trigger_rejects_whitespace_value() -> None:
    """Test that whitespace-only value raises ValueError."""
    with pytest.raises(ValueError, match="TransitionTrigger value cannot be empty"):
        TransitionTrigger("   ")
