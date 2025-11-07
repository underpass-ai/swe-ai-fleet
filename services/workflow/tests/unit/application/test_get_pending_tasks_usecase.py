"""Unit tests for GetPendingTasksUseCase."""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from core.shared.domain import Action, ActionEnum

from services.workflow.application.usecases.get_pending_tasks_usecase import (
    GetPendingTasksUseCase,
)
from services.workflow.domain.entities.state_transition import StateTransition
from services.workflow.domain.entities.workflow_state import WorkflowState
from services.workflow.domain.value_objects.role import Role
from services.workflow.domain.value_objects.story_id import StoryId
from services.workflow.domain.value_objects.task_id import TaskId
from services.workflow.domain.value_objects.workflow_state_enum import WorkflowStateEnum


@pytest.mark.asyncio
async def test_get_pending_tasks_filters_and_sorts():
    """Test GetPendingTasksUseCase filters ready tasks and sorts by priority."""
    # Create test states
    rejection = StateTransition(
        from_state="arch_reviewing",
        to_state="arch_rejected",
        action=Action(value=ActionEnum.REJECT_DESIGN),
        actor_role=Role.architect(),
        timestamp=datetime(2025, 11, 5, 9, 0, 0),
        feedback="Needs improvement",
    )

    # High priority (1 rejection, older)
    state1 = WorkflowState(
        task_id=TaskId("task-001"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.PENDING_ARCH_REVIEW,
        role_in_charge=Role.architect(),
        required_action=Action(value=ActionEnum.APPROVE_DESIGN),
        history=(rejection,),
        feedback=None,
        updated_at=datetime(2025, 11, 5, 10, 0, 0),
    )

    # Low priority (0 rejections, newer)
    state2 = WorkflowState(
        task_id=TaskId("task-002"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.PENDING_ARCH_REVIEW,
        role_in_charge=Role.architect(),
        required_action=Action(value=ActionEnum.APPROVE_DESIGN),
        history=(),
        feedback=None,
        updated_at=datetime(2025, 11, 5, 11, 0, 0),
    )

    # Wrong role (should be filtered out)
    state3 = WorkflowState(
        task_id=TaskId("task-003"),
        story_id=StoryId("story-001"),
        current_state=WorkflowStateEnum.IMPLEMENTING,
        role_in_charge=Role.developer(),
        required_action=Action(value=ActionEnum.COMMIT_CODE),
        history=(),
        feedback=None,
        updated_at=datetime(2025, 11, 5, 9, 0, 0),
    )

    # Mock repository
    repository = AsyncMock()
    repository.get_pending_by_role.return_value = [state1, state2, state3]

    # Execute use case
    use_case = GetPendingTasksUseCase(repository=repository)
    result = await use_case.execute(role=Role.architect(), limit=100)

    # Verify filtering and sorting
    assert len(result) == 2  # Only architect tasks
    assert result[0] == state1  # High priority first (has rejection)
    assert result[1] == state2  # Low priority second (no rejections)

    repository.get_pending_by_role.assert_awaited_once_with("architect", 100)


@pytest.mark.asyncio
async def test_get_pending_tasks_respects_limit():
    """Test GetPendingTasksUseCase respects limit parameter."""
    repository = AsyncMock()
    repository.get_pending_by_role.return_value = []

    use_case = GetPendingTasksUseCase(repository=repository)
    await use_case.execute(role=Role.developer(), limit=50)

    repository.get_pending_by_role.assert_awaited_once_with("developer", 50)


@pytest.mark.asyncio
async def test_get_pending_tasks_empty_result():
    """Test GetPendingTasksUseCase handles empty result."""
    repository = AsyncMock()
    repository.get_pending_by_role.return_value = []

    use_case = GetPendingTasksUseCase(repository=repository)
    result = await use_case.execute(role=Role.qa())

    assert result == []

