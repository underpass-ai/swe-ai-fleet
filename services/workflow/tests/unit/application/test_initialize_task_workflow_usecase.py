"""Unit tests for InitializeTaskWorkflowUseCase.

Tests business logic for initializing task workflows.
"""

from unittest.mock import AsyncMock

import pytest

from services.workflow.application.usecases.initialize_task_workflow_usecase import (
    InitializeTaskWorkflowUseCase,
)
from services.workflow.domain.entities.workflow_state import WorkflowState
from services.workflow.domain.value_objects.story_id import StoryId
from services.workflow.domain.value_objects.task_id import TaskId
from services.workflow.domain.value_objects.workflow_state_enum import WorkflowStateEnum


@pytest.fixture
def mock_repository():
    """Mock WorkflowStateRepositoryPort."""
    return AsyncMock()


@pytest.fixture
def mock_messaging():
    """Mock MessagingPort."""
    return AsyncMock()


@pytest.fixture
def use_case(mock_repository, mock_messaging):
    """Create InitializeTaskWorkflowUseCase with mocked dependencies."""
    return InitializeTaskWorkflowUseCase(
        repository=mock_repository,
        messaging=mock_messaging,
    )


@pytest.mark.asyncio
async def test_execute_success(use_case, mock_repository, mock_messaging):
    """Test successful workflow initialization."""
    task_id = TaskId("task-123")
    story_id = StoryId("story-456")

    result = await use_case.execute(task_id=task_id, story_id=story_id)

    # Assert: Repository called with correct state
    mock_repository.save.assert_awaited_once()
    saved_state = mock_repository.save.call_args[0][0]

    assert isinstance(saved_state, WorkflowState)
    assert saved_state.task_id == task_id
    assert saved_state.story_id == story_id
    assert saved_state.current_state == WorkflowStateEnum.TODO
    assert str(saved_state.role_in_charge) == "developer"
    assert saved_state.required_action.get_value() == "claim_task"
    assert saved_state.history == tuple()
    assert saved_state.feedback is None
    assert saved_state.retry_count == 0

    # Assert: Returns the created state
    assert result == saved_state

    # Assert: Event published
    mock_messaging.publish.assert_awaited_once()
    call_args = mock_messaging.publish.call_args

    assert call_args[1]["subject"] == "workflow.task.assigned"
    payload = call_args[1]["payload"]
    assert payload["task_id"] == "task-123"
    assert payload["story_id"] == "story-456"
    assert payload["assigned_to_role"] == "developer"
    assert payload["required_action"] == "claim_task"
    assert payload["current_state"] == "todo"


@pytest.mark.asyncio
async def test_execute_uses_factory_method(use_case, mock_repository):
    """Test that use case uses WorkflowState.create_initial() factory."""
    task_id = TaskId("task-999")
    story_id = StoryId("story-888")

    await use_case.execute(task_id=task_id, story_id=story_id)

    saved_state = mock_repository.save.call_args[0][0]

    # Verify it's an initial state (created by factory)
    assert saved_state.current_state == WorkflowStateEnum.TODO
    assert saved_state.history == tuple()
    assert saved_state.retry_count == 0


@pytest.mark.asyncio
async def test_execute_repository_error_propagates(use_case, mock_repository):
    """Test that repository errors are propagated."""
    mock_repository.save.side_effect = Exception("Database error")

    with pytest.raises(Exception, match="Database error"):
        await use_case.execute(
            task_id=TaskId("task-1"),
            story_id=StoryId("story-1"),
        )


@pytest.mark.asyncio
async def test_execute_messaging_error_propagates(use_case, mock_messaging):
    """Test that messaging errors are propagated."""
    mock_messaging.publish.side_effect = Exception("NATS error")

    with pytest.raises(Exception, match="NATS error"):
        await use_case.execute(
            task_id=TaskId("task-1"),
            story_id=StoryId("story-1"),
        )


@pytest.mark.asyncio
async def test_execute_published_event_structure(use_case, mock_messaging):
    """Test that published event has correct structure."""
    await use_case.execute(
        task_id=TaskId("task-abc"),
        story_id=StoryId("story-xyz"),
    )

    call_args = mock_messaging.publish.call_args[1]
    payload = call_args["payload"]

    # Assert required fields
    assert "task_id" in payload
    assert "story_id" in payload
    assert "assigned_to_role" in payload
    assert "required_action" in payload
    assert "current_state" in payload

    # Assert no extra fields
    assert len(payload) == 5


@pytest.mark.asyncio
async def test_execute_preserves_task_and_story_ids(use_case, mock_repository):
    """Test that task_id and story_id are preserved correctly."""
    task_id = TaskId("task-unique-123")
    story_id = StoryId("story-unique-456")

    await use_case.execute(task_id=task_id, story_id=story_id)

    saved_state = mock_repository.save.call_args[0][0]

    assert saved_state.task_id == task_id
    assert saved_state.story_id == story_id
    assert str(saved_state.task_id) == "task-unique-123"
    assert str(saved_state.story_id) == "story-unique-456"

