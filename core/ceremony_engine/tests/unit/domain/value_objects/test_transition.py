"""Unit tests for Transition value object."""

import pytest

from core.ceremony_engine.domain.value_objects.transition import Transition


def test_transition_happy_path() -> None:
    """Test creating a valid transition."""
    transition = Transition(
        from_state="INITIALIZED",
        to_state="SELECTING",
        trigger="start_selection",
        guards=(),
        description="Begin story selection",
    )

    assert transition.from_state == "INITIALIZED"
    assert transition.to_state == "SELECTING"
    assert transition.trigger == "start_selection"
    assert transition.guards == ()
    assert transition.description == "Begin story selection"


def test_transition_with_guards() -> None:
    """Test creating a transition with guards."""
    transition = Transition(
        from_state="SELECTING",
        to_state="REVIEWING",
        trigger="selection_complete",
        guards=("selection_valid", "capacity_ok"),
        description="Selection complete, ready for review",
    )

    assert len(transition.guards) == 2
    assert "selection_valid" in transition.guards
    assert "capacity_ok" in transition.guards


def test_transition_rejects_empty_from_state() -> None:
    """Test that empty from_state raises ValueError."""
    with pytest.raises(ValueError, match="Transition from_state cannot be empty"):
        Transition(
            from_state="",
            to_state="SELECTING",
            trigger="trigger",
            guards=(),
            description="Description",
        )


def test_transition_rejects_whitespace_from_state() -> None:
    """Test that whitespace-only from_state raises ValueError."""
    with pytest.raises(ValueError, match="Transition from_state cannot be empty"):
        Transition(
            from_state="   ",
            to_state="SELECTING",
            trigger="trigger",
            guards=(),
            description="Description",
        )


def test_transition_rejects_empty_to_state() -> None:
    """Test that empty to_state raises ValueError."""
    with pytest.raises(ValueError, match="Transition to_state cannot be empty"):
        Transition(
            from_state="INITIALIZED",
            to_state="",
            trigger="trigger",
            guards=(),
            description="Description",
        )


def test_transition_rejects_empty_trigger() -> None:
    """Test that empty trigger raises ValueError."""
    with pytest.raises(ValueError, match="Transition trigger cannot be empty"):
        Transition(
            from_state="INITIALIZED",
            to_state="SELECTING",
            trigger="",
            guards=(),
            description="Description",
        )


def test_transition_rejects_empty_description() -> None:
    """Test that empty description raises ValueError."""
    with pytest.raises(ValueError, match="Transition description cannot be empty"):
        Transition(
            from_state="INITIALIZED",
            to_state="SELECTING",
            trigger="trigger",
            guards=(),
            description="",
        )


def test_transition_str_representation() -> None:
    """Test string representation of transition."""
    transition = Transition(
        from_state="INITIALIZED",
        to_state="SELECTING",
        trigger="start_selection",
        guards=(),
        description="Description",
    )
    assert str(transition) == "INITIALIZED -> SELECTING (start_selection)"


def test_transition_is_immutable() -> None:
    """Test that transition is immutable (frozen dataclass)."""
    transition = Transition(
        from_state="INITIALIZED",
        to_state="SELECTING",
        trigger="trigger",
        guards=(),
        description="Description",
    )

    with pytest.raises(Exception):  # frozen dataclass raises exception on mutation
        transition.from_state = "CHANGED"  # type: ignore[misc]


def test_transition_guards_is_tuple() -> None:
    """Test that guards is stored as tuple (immutable)."""
    guards_list = ["guard1", "guard2"]
    transition = Transition(
        from_state="INITIALIZED",
        to_state="SELECTING",
        trigger="trigger",
        guards=tuple(guards_list),
        description="Description",
    )

    assert isinstance(transition.guards, tuple)
    # Tuple is immutable, so this should not affect the transition
    guards_list.append("guard3")
    assert len(transition.guards) == 2
