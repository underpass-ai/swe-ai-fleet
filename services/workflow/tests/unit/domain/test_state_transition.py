"""Unit tests for StateTransition entity."""

from datetime import datetime

import pytest
from core.shared.domain import Action, ActionEnum

from services.workflow.domain.entities.state_transition import StateTransition
from services.workflow.domain.value_objects.role import Role


def test_state_transition_creation_success():
    """Test StateTransition creation with valid data."""
    transition = StateTransition(
        from_state="implementing",
        to_state="dev_completed",
        action=Action(value=ActionEnum.COMMIT_CODE),
        actor_role=Role.developer(),
        timestamp=datetime(2025, 11, 5, 10, 30, 0),
        feedback=None,
    )

    assert transition.from_state == "implementing"
    assert transition.to_state == "dev_completed"
    assert transition.action.value == ActionEnum.COMMIT_CODE
    assert transition.actor_role == Role.developer()
    assert transition.feedback is None


def test_state_transition_empty_from_state_raises_error():
    """Test StateTransition with empty from_state raises ValueError."""
    with pytest.raises(ValueError, match="from_state cannot be empty"):
        StateTransition(
            from_state="",
            to_state="dev_completed",
            action=Action(value=ActionEnum.COMMIT_CODE),
            actor_role=Role.developer(),
            timestamp=datetime.now(),
        )


def test_state_transition_empty_to_state_raises_error():
    """Test StateTransition with empty to_state raises ValueError."""
    with pytest.raises(ValueError, match="to_state cannot be empty"):
        StateTransition(
            from_state="implementing",
            to_state="",
            action=Action(value=ActionEnum.COMMIT_CODE),
            actor_role=Role.developer(),
            timestamp=datetime.now(),
        )


def test_state_transition_rejection_requires_feedback():
    """Test rejection actions require substantial feedback (>= 10 chars)."""
    # Missing feedback
    with pytest.raises(ValueError, match="requires substantial feedback"):
        StateTransition(
            from_state="arch_reviewing",
            to_state="arch_rejected",
            action=Action(value=ActionEnum.REJECT_DESIGN),
            actor_role=Role.architect(),
            timestamp=datetime.now(),
            feedback=None,
        )

    # Feedback too short
    with pytest.raises(ValueError, match="requires substantial feedback"):
        StateTransition(
            from_state="arch_reviewing",
            to_state="arch_rejected",
            action=Action(value=ActionEnum.REJECT_DESIGN),
            actor_role=Role.architect(),
            timestamp=datetime.now(),
            feedback="short",  # Only 5 chars
        )

    # Valid feedback
    transition = StateTransition(
        from_state="arch_reviewing",
        to_state="arch_rejected",
        action=Action(value=ActionEnum.REJECT_DESIGN),
        actor_role=Role.architect(),
        timestamp=datetime.now(),
        feedback="The design has architectural flaws in error handling",
    )
    assert transition.feedback is not None


def test_state_transition_is_rejection():
    """Test is_rejection() method."""
    rejection = StateTransition(
        from_state="arch_reviewing",
        to_state="arch_rejected",
        action=Action(value=ActionEnum.REJECT_DESIGN),
        actor_role=Role.architect(),
        timestamp=datetime.now(),
        feedback="Architecture needs improvement",
    )

    assert rejection.is_rejection() is True
    assert rejection.is_approval() is False


def test_state_transition_is_approval():
    """Test is_approval() method."""
    approval = StateTransition(
        from_state="arch_reviewing",
        to_state="arch_approved",
        action=Action(value=ActionEnum.APPROVE_DESIGN),
        actor_role=Role.architect(),
        timestamp=datetime.now(),
    )

    assert approval.is_approval() is True
    assert approval.is_rejection() is False


def test_state_transition_is_system_action():
    """Test is_system_action() method."""
    system_transition = StateTransition(
        from_state="dev_completed",
        to_state="pending_arch_review",
        action=Action(value=ActionEnum.REQUEST_REVIEW),
        actor_role=Role.system(),
        timestamp=datetime.now(),
    )

    assert system_transition.is_system_action() is True

    user_transition = StateTransition(
        from_state="implementing",
        to_state="dev_completed",
        action=Action(value=ActionEnum.COMMIT_CODE),
        actor_role=Role.developer(),
        timestamp=datetime.now(),
    )

    assert user_transition.is_system_action() is False


def test_state_transition_immutable():
    """Test StateTransition is immutable (frozen)."""
    transition = StateTransition(
        from_state="implementing",
        to_state="dev_completed",
        action=Action(value=ActionEnum.COMMIT_CODE),
        actor_role=Role.developer(),
        timestamp=datetime.now(),
    )

    with pytest.raises(AttributeError):
        transition.from_state = "other_state"  # type: ignore

