"""Tests for create_task handler."""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timezone

from planning.domain.entities.task import Task
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.statuses.task_status import TaskStatus
from planning.domain.value_objects.statuses.task_type import TaskType
from planning.gen import planning_pb2
from planning.infrastructure.grpc.handlers.create_task_handler import create_task


@pytest.fixture
def mock_use_case():
    """Create mock CreateTaskUseCase."""
    return AsyncMock()


@pytest.fixture
def mock_context():
    """Create mock gRPC context."""
    return Mock()


@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    now = datetime.now(timezone.utc)
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
async def test_create_task_success(mock_use_case, mock_context, sample_task):
    """Test creating task successfully."""
    # Arrange
    mock_use_case.execute.return_value = sample_task
    request = planning_pb2.CreateTaskRequest(
        story_id="STORY-001",
        plan_id="PLAN-001",
        title="Test Task",
        description="Test description",
        type=TaskType.DEVELOPMENT.value,
    )

    # Act
    response = await create_task(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    assert "Task created" in response.message
    assert response.task.task_id == "TASK-001"
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_task_validation_error(mock_use_case, mock_context):
    """Test create with validation error."""
    # Arrange
    mock_use_case.execute.side_effect = ValueError("Story not found")
    request = planning_pb2.CreateTaskRequest(
        story_id="INVALID",
        plan_id="PLAN-001",
        title="Test",
        description="",
        type="",
    )

    # Act
    response = await create_task(request, mock_context, mock_use_case)

    # Assert
    assert response.success is False
    assert "Story not found" in response.message
    mock_context.set_code.assert_called_once()


@pytest.mark.asyncio
async def test_create_task_internal_error(mock_use_case, mock_context):
    """Test create with internal error."""
    # Arrange
    mock_use_case.execute.side_effect = Exception("Database error")
    request = planning_pb2.CreateTaskRequest(
        story_id="STORY-001",
        plan_id="PLAN-001",
        title="Test",
        description="Test",
        type=TaskType.DEVELOPMENT.value,
    )

    # Act
    response = await create_task(request, mock_context, mock_use_case)

    # Assert
    assert response.success is False
    assert "Internal error" in response.message
    mock_context.set_code.assert_called_once()

