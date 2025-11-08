"""Unit tests for GetWorkflowStateUseCase."""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from core.shared.domain import Action, ActionEnum

from services.workflow.application.usecases.get_workflow_state_usecase import (
    GetWorkflowStateUseCase,
)
from services.workflow.domain.entities.workflow_state import WorkflowState
from services.workflow.domain.value_objects.role import Role
from services.workflow.domain.value_objects.story_id import StoryId
from services.workflow.domain.value_objects.task_id import TaskId
from services.workflow.domain.value_objects.workflow_state_enum import WorkflowStateEnum


@pytest.mark.asyncio
async def test_get_workflow_state_success():
    """Test GetWorkflowStateUseCase returns state when found."""
    # Mock repository
    repository = AsyncMock()

    expected_state = WorkflowState(
        task_id=TaskId("task-001"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.IMPLEMENTING,
        role_in_charge=Role.developer(),
        required_action=Action(value=ActionEnum.COMMIT_CODE),
        history=(),
        feedback=None,
        updated_at=datetime(2025, 11, 5, 10, 0, 0),
    )

    repository.get_state.return_value = expected_state

    # Execute use case
    use_case = GetWorkflowStateUseCase(repository=repository)
    result = await use_case.execute(task_id=TaskId("task-001"))

    # Verify
    assert result == expected_state
    repository.get_state.assert_awaited_once_with(TaskId("task-001"))


@pytest.mark.asyncio
async def test_get_workflow_state_not_found_returns_none():
    """Test GetWorkflowStateUseCase returns None when task not found."""
    # Mock repository (returns None)
    repository = AsyncMock()
    repository.get_state.return_value = None

    # Execute use case
    use_case = GetWorkflowStateUseCase(repository=repository)
    result = await use_case.execute(task_id=TaskId("task-999"))

    # Verify
    assert result is None
    repository.get_state.assert_awaited_once_with(TaskId("task-999"))

