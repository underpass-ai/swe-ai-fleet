"""Unit tests for ExecuteWorkflowActionUseCase."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.agents_and_tools.agents.domain.entities.rbac.action import Action, ActionEnum
from services.workflow.application.usecases.execute_workflow_action_usecase import (
    ExecuteWorkflowActionUseCase,
)
from services.workflow.domain.entities.workflow_state import WorkflowState
from services.workflow.domain.exceptions.workflow_transition_error import (
    WorkflowTransitionError,
)
from services.workflow.domain.value_objects.role import Role
from services.workflow.domain.value_objects.story_id import StoryId
from services.workflow.domain.value_objects.task_id import TaskId
from services.workflow.domain.value_objects.workflow_state_enum import WorkflowStateEnum


@pytest.mark.asyncio
async def test_execute_workflow_action_success():
    """Test ExecuteWorkflowActionUseCase executes transition successfully."""
    # Mock dependencies
    repository = AsyncMock()
    messaging = AsyncMock()
    state_machine = MagicMock()

    # Setup: current state
    current_state = WorkflowState(
        task_id=TaskId("task-001"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.IMPLEMENTING,
        role_in_charge=Role.developer(),
        required_action=Action(value=ActionEnum.COMMIT_CODE),
        history=(),
        feedback=None,
        updated_at=datetime(2025, 11, 5, 10, 0, 0),
    )

    # Setup: new state after transition
    new_state = WorkflowState(
        task_id=TaskId("task-001"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.PENDING_ARCH_REVIEW,
        role_in_charge=Role.architect(),
        required_action=Action(value=ActionEnum.APPROVE_DESIGN),
        history=(),
        feedback=None,
        updated_at=datetime(2025, 11, 5, 11, 0, 0),
    )

    repository.get_state.return_value = current_state
    state_machine.can_execute_action.return_value = True
    state_machine.execute_transition.return_value = new_state

    # Execute use case
    use_case = ExecuteWorkflowActionUseCase(
        repository=repository,
        messaging=messaging,
        state_machine=state_machine,
    )

    result = await use_case.execute(
        task_id=TaskId("task-001"),
        action=Action(value=ActionEnum.COMMIT_CODE),
        actor_role=Role.developer(),
        timestamp=datetime(2025, 11, 5, 11, 0, 0),
        feedback=None,
    )

    # Verify result
    assert result == new_state

    # Verify repository called
    repository.get_state.assert_awaited_once_with(TaskId("task-001"))
    repository.save_state.assert_awaited_once_with(new_state)

    # Verify state machine called
    state_machine.can_execute_action.assert_called_once()
    state_machine.execute_transition.assert_called_once()

    # Verify events published
    messaging.publish_state_changed.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_workflow_action_task_not_found_raises_error():
    """Test ExecuteWorkflowActionUseCase raises ValueError when task not found."""
    repository = AsyncMock()
    repository.get_state.return_value = None

    messaging = AsyncMock()
    state_machine = MagicMock()

    use_case = ExecuteWorkflowActionUseCase(
        repository=repository,
        messaging=messaging,
        state_machine=state_machine,
    )

    with pytest.raises(ValueError, match="not found in workflow"):
        await use_case.execute(
            task_id=TaskId("task-999"),
            action=Action(value=ActionEnum.COMMIT_CODE),
            actor_role=Role.developer(),
            timestamp=datetime.now(),
        )


@pytest.mark.asyncio
async def test_execute_workflow_action_not_allowed_raises_error():
    """Test ExecuteWorkflowActionUseCase raises WorkflowTransitionError when action not allowed."""
    repository = AsyncMock()
    messaging = AsyncMock()
    state_machine = MagicMock()

    current_state = WorkflowState(
        task_id=TaskId("task-001"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.IMPLEMENTING,
        role_in_charge=Role.developer(),
        required_action=Action(value=ActionEnum.COMMIT_CODE),
        history=(),
        feedback=None,
        updated_at=datetime.now(),
    )

    repository.get_state.return_value = current_state
    state_machine.can_execute_action.return_value = False  # Not allowed

    use_case = ExecuteWorkflowActionUseCase(
        repository=repository,
        messaging=messaging,
        state_machine=state_machine,
    )

    with pytest.raises(WorkflowTransitionError, match="not allowed"):
        await use_case.execute(
            task_id=TaskId("task-001"),
            action=Action(value=ActionEnum.APPROVE_DESIGN),  # Wrong action
            actor_role=Role.architect(),  # Wrong role
            timestamp=datetime.now(),
        )


@pytest.mark.asyncio
async def test_execute_workflow_action_publishes_task_assigned_when_waiting():
    """Test use case publishes task_assigned event when state is waiting for role."""
    repository = AsyncMock()
    messaging = AsyncMock()
    state_machine = MagicMock()

    current_state = WorkflowState(
        task_id=TaskId("task-001"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.IMPLEMENTING,
        role_in_charge=Role.developer(),
        required_action=Action(value=ActionEnum.COMMIT_CODE),
        history=(),
        feedback=None,
        updated_at=datetime.now(),
    )

    # New state is waiting for architect
    new_state = WorkflowState(
        task_id=TaskId("task-001"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.PENDING_ARCH_REVIEW,
        role_in_charge=Role.architect(),
        required_action=Action(value=ActionEnum.APPROVE_DESIGN),
        history=(),
        feedback=None,
        updated_at=datetime.now(),
    )

    repository.get_state.return_value = current_state
    state_machine.can_execute_action.return_value = True
    state_machine.execute_transition.return_value = new_state

    use_case = ExecuteWorkflowActionUseCase(
        repository=repository,
        messaging=messaging,
        state_machine=state_machine,
    )

    await use_case.execute(
        task_id=TaskId("task-001"),
        action=Action(value=ActionEnum.COMMIT_CODE),
        actor_role=Role.developer(),
        timestamp=datetime.now(),
    )

    # Verify task_assigned published (because should_notify_role_assignment() == True)
    messaging.publish_task_assigned.assert_awaited_once()
    messaging.publish_validation_required.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_workflow_action_publishes_task_completed_when_terminal():
    """Test use case publishes task_completed event when state becomes terminal."""
    repository = AsyncMock()
    messaging = AsyncMock()
    state_machine = MagicMock()

    current_state = WorkflowState(
        task_id=TaskId("task-001"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.PO_APPROVED,
        role_in_charge=None,
        required_action=None,
        history=(),
        feedback=None,
        updated_at=datetime.now(),
    )

    # New state is DONE (terminal)
    new_state = WorkflowState(
        task_id=TaskId("task-001"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.DONE,
        role_in_charge=None,
        required_action=None,
        history=(),
        feedback=None,
        updated_at=datetime.now(),
    )

    repository.get_state.return_value = current_state
    state_machine.can_execute_action.return_value = True
    state_machine.execute_transition.return_value = new_state

    use_case = ExecuteWorkflowActionUseCase(
        repository=repository,
        messaging=messaging,
        state_machine=state_machine,
    )

    await use_case.execute(
        task_id=TaskId("task-001"),
        action=Action(value=ActionEnum.APPROVE_STORY),
        actor_role=Role.po(),
        timestamp=datetime.now(),
    )

    # Verify task_completed published (because is_terminal() == True)
    messaging.publish_task_completed.assert_awaited_once()

