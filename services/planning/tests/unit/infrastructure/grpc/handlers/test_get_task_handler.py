"""Tests for get_task handler."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from planning.gen import planning_pb2

from planning.domain.entities.task import Task
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.statuses.task_status import TaskStatus
from planning.domain.value_objects.statuses.task_type import TaskType
from planning.infrastructure.grpc.handlers.get_task_handler import get_task_handler


@pytest.fixture
def mock_use_case():
    """Create mock GetTaskUseCase."""
    return AsyncMock()


@pytest.fixture
def mock_context():
    """Create mock gRPC context."""
    return Mock()


@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    now = datetime.now(UTC)
    return Task(
        task_id=TaskId("TASK-001"),
        plan_id=PlanId("PLAN-001"),
        story_id=StoryId("STORY-001"),
        title="Test Task",
        description="Test description",
        type=TaskType.DEVELOPMENT,
        status=TaskStatus.TODO,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_get_task_success(mock_use_case, mock_context, sample_task):
    """Test getting task successfully."""
    # Arrange
    mock_use_case.execute.return_value = sample_task
    request = planning_pb2.GetTaskRequest(task_id="TASK-001")

    # Act
    response = await get_task_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.task.task_id == "TASK-001"
    assert response.task.title == "Test Task"
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_task_not_found(mock_use_case, mock_context):
    """Test getting task that doesn't exist."""
    # Arrange
    mock_use_case.execute.return_value = None
    request = planning_pb2.GetTaskRequest(task_id="NONEXISTENT")

    # Act
    response = await get_task_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.task.task_id == ""  # Empty task
    mock_context.set_code.assert_called_once()


@pytest.mark.asyncio
async def test_get_task_internal_error(mock_use_case, mock_context):
    """Test get task with internal error."""
    # Arrange
    mock_use_case.execute.side_effect = Exception("Database error")
    request = planning_pb2.GetTaskRequest(task_id="TASK-001")

    # Act
    response = await get_task_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.task.task_id == ""  # Empty task on error
    mock_context.set_code.assert_called_once()

