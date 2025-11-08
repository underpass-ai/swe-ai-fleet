"""Unit tests for WorkflowState factory methods.

Tests WorkflowState.create_initial() and Tell, Don't Ask methods.
"""

from datetime import UTC, datetime

import pytest
from core.shared.domain import ActionEnum

from services.workflow.domain.entities.workflow_state import WorkflowState
from services.workflow.domain.value_objects.role import Role
from services.workflow.domain.value_objects.story_id import StoryId
from services.workflow.domain.value_objects.task_id import TaskId
from services.workflow.domain.value_objects.workflow_state_enum import WorkflowStateEnum


def test_create_initial_success():
    """Test WorkflowState.create_initial() factory method."""
    task_id = TaskId("task-123")
    story_id = StoryId("story-456")

    state = WorkflowState.create_initial(task_id=task_id, story_id=story_id, initial_role=Role("developer"))

    assert state.task_id == task_id
    assert state.story_id == story_id
    assert state.current_state == WorkflowStateEnum.TODO
    assert str(state.role_in_charge) == "developer"
    assert state.required_action.get_value() == "claim_task"
    assert state.history == tuple()
    assert state.feedback is None
    assert state.retry_count == 0
    assert isinstance(state.updated_at, datetime)


def test_create_initial_different_ids():
    """Test factory creates different states for different IDs."""
    state1 = WorkflowState.create_initial(
        task_id=TaskId("task-1"),
        story_id=StoryId("story-1"),
        initial_role=Role("developer"),
    )
    state2 = WorkflowState.create_initial(
        task_id=TaskId("task-2"),
        story_id=StoryId("story-2"),
        initial_role=Role("qa"),
    )

    assert state1.task_id != state2.task_id
    assert state1.story_id != state2.story_id
    assert state1.current_state == state2.current_state  # Both TODO


def test_get_current_state_value():
    """Test get_current_state_value() Tell, Don't Ask method."""
    state = WorkflowState.create_initial(
        task_id=TaskId("task-1"),
        story_id=StoryId("story-1"),
        initial_role=Role("developer"),
    )

    assert state.get_current_state_value() == "todo"
    assert isinstance(state.get_current_state_value(), str)


def test_get_required_action_value():
    """Test get_required_action_value() Tell, Don't Ask method."""
    state = WorkflowState.create_initial(
        task_id=TaskId("task-1"),
        story_id=StoryId("story-1"),
        initial_role=Role("developer"),
    )

    assert state.get_required_action_value() == "claim_task"
    assert isinstance(state.get_required_action_value(), str)


def test_get_required_action_value_when_none():
    """Test get_required_action_value() returns NO_ACTION when None."""
    state = WorkflowState(
        task_id=TaskId("task-1"),
        story_id=StoryId("story-1"),
        current_state=WorkflowStateEnum.DONE,
        role_in_charge=None,
        required_action=None,  # Terminal state
        history=tuple(),
        feedback=None,
        updated_at=datetime.now(),
        retry_count=0,
    )

    assert state.get_required_action_value() == ActionEnum.NO_ACTION.value


def test_get_role_in_charge_value():
    """Test get_role_in_charge_value() Tell, Don't Ask method."""
    state = WorkflowState.create_initial(
        task_id=TaskId("task-1"),
        story_id=StoryId("story-1"),
        initial_role=Role("developer"),
    )

    assert state.get_role_in_charge_value() == "developer"
    assert isinstance(state.get_role_in_charge_value(), str)


def test_get_role_in_charge_value_when_none():
    """Test get_role_in_charge_value() returns NO_ROLE when None."""
    from services.workflow.domain.value_objects.role import NO_ROLE

    state = WorkflowState(
        task_id=TaskId("task-1"),
        story_id=StoryId("story-1"),
        current_state=WorkflowStateEnum.DONE,
        role_in_charge=None,  # Terminal state
        required_action=None,
        history=tuple(),
        feedback=None,
        updated_at=datetime.now(),
        retry_count=0,
    )

    assert state.get_role_in_charge_value() == NO_ROLE


def test_create_initial_has_no_history():
    """Test that initial state has empty history."""
    state = WorkflowState.create_initial(
        task_id=TaskId("task-1"),
        story_id=StoryId("story-1"),
        initial_role=Role("developer"),
    )

    assert len(state.history) == 0
    assert state.history == tuple()


def test_create_initial_sets_updated_at():
    """Test that create_initial sets updated_at timestamp."""
    before = datetime.now(UTC)  # SUT uses datetime.now(UTC)
    state = WorkflowState.create_initial(
        task_id=TaskId("task-1"),
        story_id=StoryId("story-1"),
        initial_role=Role("developer"),
    )
    after = datetime.now(UTC)  # Match SUT behavior

    assert before <= state.updated_at <= after


def test_workflow_state_immutable():
    """Test that WorkflowState is immutable (frozen=True)."""
    state = WorkflowState.create_initial(
        task_id=TaskId("task-1"),
        story_id=StoryId("story-1"),
        initial_role=Role("developer"),
    )

    with pytest.raises(AttributeError):
        state.retry_count = 5  # type: ignore


def test_create_initial_encapsulates_domain_knowledge():
    """Test that factory encapsulates initial state domain knowledge."""
    # The factory knows:
    # - Initial state is TODO
    # - Developer is responsible
    # - First action is claim_task
    state = WorkflowState.create_initial(
        task_id=TaskId("task-1"),
        story_id=StoryId("story-1"),
        initial_role=Role("developer"),
    )

    # This domain knowledge should NOT be in application/infrastructure
    assert state.current_state == WorkflowStateEnum.TODO
    assert str(state.role_in_charge) == "developer"
    assert state.required_action.value == ActionEnum.CLAIM_TASK

