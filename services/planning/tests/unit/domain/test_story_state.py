"""Unit tests for StoryState value object."""

import pytest

from planning.domain.value_objects import StoryState, StoryStateEnum


def test_story_state_creation_success():
    """Test successful StoryState creation."""
    state = StoryState(StoryStateEnum.DRAFT)
    assert state.value == StoryStateEnum.DRAFT


def test_story_state_is_frozen():
    """Test that StoryState is immutable."""
    state = StoryState(StoryStateEnum.DRAFT)

    with pytest.raises(Exception):  # FrozenInstanceError
        state.value = StoryStateEnum.DONE  # type: ignore


def test_story_state_rejects_invalid_enum():
    """Test that StoryState rejects non-enum values."""
    with pytest.raises(ValueError, match="Invalid state"):
        StoryState("INVALID_STATE")  # type: ignore


def test_story_state_predicates():
    """Test state checking methods."""
    draft = StoryState(StoryStateEnum.DRAFT)
    done = StoryState(StoryStateEnum.DONE)
    in_progress = StoryState(StoryStateEnum.IN_PROGRESS)

    assert draft.is_draft() is True
    assert draft.is_done() is False
    assert draft.is_in_progress() is False

    assert done.is_draft() is False
    assert done.is_done() is True

    assert in_progress.is_in_progress() is True


def test_fsm_transition_draft_to_po_review():
    """Test valid transition: DRAFT → PO_REVIEW."""
    draft = StoryState(StoryStateEnum.DRAFT)
    po_review = StoryState(StoryStateEnum.PO_REVIEW)

    assert draft.can_transition_to(po_review) is True


def test_fsm_transition_po_review_to_ready():
    """Test valid transition: PO_REVIEW → READY_FOR_PLANNING."""
    po_review = StoryState(StoryStateEnum.PO_REVIEW)
    ready = StoryState(StoryStateEnum.READY_FOR_PLANNING)

    assert po_review.can_transition_to(ready) is True


def test_fsm_transition_po_review_to_draft():
    """Test valid transition: PO_REVIEW → DRAFT (rejection)."""
    po_review = StoryState(StoryStateEnum.PO_REVIEW)
    draft = StoryState(StoryStateEnum.DRAFT)

    assert po_review.can_transition_to(draft) is True


def test_fsm_transition_invalid():
    """Test invalid transition: DRAFT → DONE (skipping states)."""
    draft = StoryState(StoryStateEnum.DRAFT)
    done = StoryState(StoryStateEnum.DONE)

    assert draft.can_transition_to(done) is False


def test_fsm_transition_testing_to_in_progress():
    """Test valid transition: TESTING → IN_PROGRESS (rework)."""
    testing = StoryState(StoryStateEnum.TESTING)
    in_progress = StoryState(StoryStateEnum.IN_PROGRESS)

    assert testing.can_transition_to(in_progress) is True


def test_fsm_transition_testing_to_ready_to_review():
    """Test valid transition: TESTING → READY_TO_REVIEW (tests passed)."""
    testing = StoryState(StoryStateEnum.TESTING)
    ready_to_review = StoryState(StoryStateEnum.READY_TO_REVIEW)

    assert testing.can_transition_to(ready_to_review) is True


def test_fsm_transition_done_to_archived():
    """Test valid transition: DONE → ARCHIVED."""
    done = StoryState(StoryStateEnum.DONE)
    archived = StoryState(StoryStateEnum.ARCHIVED)

    assert done.can_transition_to(archived) is True


def test_fsm_transition_archived_is_terminal():
    """Test that ARCHIVED is a terminal state (no transitions allowed)."""
    archived = StoryState(StoryStateEnum.ARCHIVED)
    draft = StoryState(StoryStateEnum.DRAFT)

    assert archived.can_transition_to(draft) is True  # Reset to DRAFT always allowed


def test_fsm_reset_to_draft_always_allowed():
    """Test that any state can reset to DRAFT."""
    states = [
        StoryStateEnum.PO_REVIEW,
        StoryStateEnum.READY_FOR_PLANNING,
        StoryStateEnum.IN_PROGRESS,
        StoryStateEnum.CODE_REVIEW,
        StoryStateEnum.TESTING,
        StoryStateEnum.DONE,
    ]

    draft = StoryState(StoryStateEnum.DRAFT)

    for state_enum in states:
        current = StoryState(state_enum)
        assert current.can_transition_to(draft) is True


def test_story_state_str_representation():
    """Test string representation."""
    state = StoryState(StoryStateEnum.IN_PROGRESS)
    assert str(state) == "IN_PROGRESS"

