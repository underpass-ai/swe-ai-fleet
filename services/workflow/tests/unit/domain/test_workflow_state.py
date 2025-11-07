"""Unit tests for WorkflowState entity."""

from datetime import datetime

import pytest
from core.shared.domain import Action, ActionEnum

from services.workflow.domain.entities.state_transition import StateTransition
from services.workflow.domain.entities.workflow_state import WorkflowState
from services.workflow.domain.value_objects.role import Role
from services.workflow.domain.value_objects.story_id import StoryId
from services.workflow.domain.value_objects.task_id import TaskId
from services.workflow.domain.value_objects.workflow_state_enum import WorkflowStateEnum


def test_workflow_state_creation_success():
    """Test WorkflowState creation with valid data."""
    state = WorkflowState(
        task_id=TaskId("task-001"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.IMPLEMENTING,
        role_in_charge=Role.developer(),
        required_action=Action(value=ActionEnum.COMMIT_CODE),
        history=(),
        feedback=None,
        updated_at=datetime(2025, 11, 5, 10, 0, 0),
        retry_count=0,
    )

    assert state.task_id.value == "task-001"
    assert state.current_state == WorkflowStateEnum.IMPLEMENTING
    assert state.role_in_charge == Role.developer()
    assert state.retry_count == 0


def test_workflow_state_negative_retry_count_raises_error():
    """Test WorkflowState with negative retry_count raises ValueError."""
    with pytest.raises(ValueError, match="retry_count cannot be negative"):
        WorkflowState(
            task_id=TaskId("task-001"),
            story_id=StoryId("story-001"),
            current_state=WorkflowStateEnum.IMPLEMENTING,
            role_in_charge=Role.developer(),
            required_action=Action(value=ActionEnum.COMMIT_CODE),
            history=(),
            feedback=None,
            updated_at=datetime.now(),
            retry_count=-1,  # Invalid
        )


def test_workflow_state_is_terminal():
    """Test is_terminal() method."""
    done_state = WorkflowState(
        task_id=TaskId("task-001"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.DONE,
        role_in_charge=None,
        required_action=None,
        history=(),
        feedback=None,
        updated_at=datetime.now(),
    )

    assert done_state.is_terminal() is True

    active_state = WorkflowState(
        task_id=TaskId("task-001"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.IMPLEMENTING,
        role_in_charge=Role.developer(),
        required_action=Action(value=ActionEnum.COMMIT_CODE),
        history=(),
        feedback=None,
        updated_at=datetime.now(),
    )

    assert active_state.is_terminal() is False


def test_workflow_state_is_ready_for_role():
    """Test is_ready_for_role() method (Tell, Don't Ask)."""
    state = WorkflowState(
        task_id=TaskId("task-001"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.PENDING_ARCH_REVIEW,
        role_in_charge=Role.architect(),
        required_action=Action(value=ActionEnum.APPROVE_DESIGN),
        history=(),
        feedback=None,
        updated_at=datetime.now(),
    )

    assert state.is_ready_for_role(Role.architect()) is True
    assert state.is_ready_for_role(Role.developer()) is False


def test_workflow_state_should_notify_role_assignment():
    """Test should_notify_role_assignment() method."""
    # Waiting state with role
    waiting_state = WorkflowState(
        task_id=TaskId("task-001"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.PENDING_ARCH_REVIEW,
        role_in_charge=Role.architect(),
        required_action=Action(value=ActionEnum.APPROVE_DESIGN),
        history=(),
        feedback=None,
        updated_at=datetime.now(),
    )

    assert waiting_state.should_notify_role_assignment() is True

    # Terminal state (no notification)
    done_state = WorkflowState(
        task_id=TaskId("task-001"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.DONE,
        role_in_charge=None,
        required_action=None,
        history=(),
        feedback=None,
        updated_at=datetime.now(),
    )

    assert done_state.should_notify_role_assignment() is False


def test_workflow_state_get_rejection_count():
    """Test get_rejection_count() method."""
    transition1 = StateTransition(
        from_state="arch_reviewing",
        to_state="arch_rejected",
        action=Action(value=ActionEnum.REJECT_DESIGN),
        actor_role=Role.architect(),
        timestamp=datetime(2025, 11, 5, 10, 0, 0),
        feedback="Needs improvement",
    )

    transition2 = StateTransition(
        from_state="implementing",
        to_state="dev_completed",
        action=Action(value=ActionEnum.COMMIT_CODE),
        actor_role=Role.developer(),
        timestamp=datetime(2025, 11, 5, 11, 0, 0),
    )

    transition3 = StateTransition(
        from_state="qa_testing",
        to_state="qa_failed",
        action=Action(value=ActionEnum.REJECT_TESTS),
        actor_role=Role.qa(),
        timestamp=datetime(2025, 11, 5, 12, 0, 0),
        feedback="Tests incomplete",
    )

    state = WorkflowState(
        task_id=TaskId("task-001"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.IMPLEMENTING,
        role_in_charge=Role.developer(),
        required_action=Action(value=ActionEnum.COMMIT_CODE),
        history=(transition1, transition2, transition3),
        feedback=None,
        updated_at=datetime.now(),
    )

    assert state.get_rejection_count() == 2  # 2 rejections


def test_workflow_state_with_new_state():
    """Test with_new_state() immutable update method."""
    original = WorkflowState(
        task_id=TaskId("task-001"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.IMPLEMENTING,
        role_in_charge=Role.developer(),
        required_action=Action(value=ActionEnum.COMMIT_CODE),
        history=(),
        feedback=None,
        updated_at=datetime(2025, 11, 5, 10, 0, 0),
        retry_count=0,
    )

    transition = StateTransition(
        from_state="implementing",
        to_state="dev_completed",
        action=Action(value=ActionEnum.COMMIT_CODE),
        actor_role=Role.developer(),
        timestamp=datetime(2025, 11, 5, 11, 0, 0),
    )

    new_state = original.with_new_state(
        new_state=WorkflowStateEnum.DEV_COMPLETED,
        new_role=None,
        new_action=None,
        transition=transition,
    )

    # New state updated
    assert new_state.current_state == WorkflowStateEnum.DEV_COMPLETED
    assert new_state.role_in_charge is None
    assert len(new_state.history) == 1
    assert new_state.history[0] == transition

    # Original unchanged (immutable)
    assert original.current_state == WorkflowStateEnum.IMPLEMENTING
    assert len(original.history) == 0


def test_workflow_state_with_retry():
    """Test with_retry() method (reset to TODO)."""
    state_with_history = WorkflowState(
        task_id=TaskId("task-001"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.IMPLEMENTING,
        role_in_charge=Role.developer(),
        required_action=Action(value=ActionEnum.COMMIT_CODE),
        history=(),
        feedback="Previous feedback",
        updated_at=datetime(2025, 11, 5, 10, 0, 0),
        retry_count=1,
    )

    retry_timestamp = datetime(2025, 11, 5, 12, 0, 0)
    retried_state = state_with_history.with_retry(retry_timestamp)

    # Reset to TODO
    assert retried_state.current_state == WorkflowStateEnum.TODO
    assert retried_state.role_in_charge is None
    assert retried_state.required_action is None
    assert retried_state.feedback is None  # Cleared
    assert retried_state.retry_count == 2  # Incremented
    assert len(retried_state.history) == 1  # Retry transition added
    assert retried_state.history[0].action.value == ActionEnum.RETRY


def test_workflow_state_immutable():
    """Test WorkflowState is immutable (frozen)."""
    state = WorkflowState(
        task_id=TaskId("task-001"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.IMPLEMENTING,
        role_in_charge=Role.developer(),
        required_action=Action(value=ActionEnum.COMMIT_CODE),
        history=(),
        feedback=None,
        updated_at=datetime.now(),
    )

    with pytest.raises(AttributeError):
        state.current_state = WorkflowStateEnum.DONE  # type: ignore

