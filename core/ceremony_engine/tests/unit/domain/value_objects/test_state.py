"""Unit tests for State value object."""

import pytest

from core.ceremony_engine.domain.value_objects.state import State


def test_state_happy_path() -> None:
    """Test creating a valid state."""
    state = State(id="INITIALIZED", description="Ceremony started")

    assert state.id == "INITIALIZED"
    assert state.description == "Ceremony started"
    assert state.terminal is False
    assert state.initial is False


def test_state_with_flags() -> None:
    """Test creating a state with terminal and initial flags."""
    state = State(
        id="COMPLETED", description="Ceremony completed", terminal=True, initial=False
    )

    assert state.id == "COMPLETED"
    assert state.terminal is True
    assert state.initial is False


def test_state_rejects_empty_id() -> None:
    """Test that empty id raises ValueError."""
    with pytest.raises(ValueError, match="State id cannot be empty"):
        State(id="", description="Description")


def test_state_rejects_whitespace_id() -> None:
    """Test that whitespace-only id raises ValueError."""
    with pytest.raises(ValueError, match="State id cannot be empty"):
        State(id="   ", description="Description")


def test_state_rejects_lowercase_id() -> None:
    """Test that lowercase id raises ValueError."""
    with pytest.raises(ValueError, match="State id must be UPPERCASE"):
        State(id="initialized", description="Description")


def test_state_rejects_mixed_case_id() -> None:
    """Test that mixed case id raises ValueError."""
    with pytest.raises(ValueError, match="State id must be UPPERCASE"):
        State(id="Initialized", description="Description")


def test_state_rejects_empty_description() -> None:
    """Test that empty description raises ValueError."""
    with pytest.raises(ValueError, match="State description cannot be empty"):
        State(id="INITIALIZED", description="")


def test_state_rejects_whitespace_description() -> None:
    """Test that whitespace-only description raises ValueError."""
    with pytest.raises(ValueError, match="State description cannot be empty"):
        State(id="INITIALIZED", description="   ")


def test_state_str_representation() -> None:
    """Test string representation of state."""
    state = State(id="INITIALIZED", description="Ceremony started")
    assert str(state) == "INITIALIZED"


def test_state_is_immutable() -> None:
    """Test that state is immutable (frozen dataclass)."""
    state = State(id="INITIALIZED", description="Description")

    with pytest.raises(Exception):  # frozen dataclass raises exception on mutation
        state.id = "CHANGED"  # type: ignore[misc]
