"""Tests for get_task handler."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import grpc
import pytest
from planning.domain.entities.task import Task
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.statuses.task_status import TaskStatus
from planning.domain.value_objects.statuses.task_type import TaskType
from planning.gen import planning_pb2
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
        story_id=StoryId("STORY-001"),
        title="Test Task",
        created_at=now,
        updated_at=now,
        plan_id=PlanId("PLAN-001"),
        description="Test description",
        type=TaskType.DEVELOPMENT,
        status=TaskStatus.TODO,
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
    assert response.success is False
    assert "Internal error" in response.message
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)


@pytest.mark.asyncio
async def test_get_task_invalid_task_id_format(mock_use_case, mock_context):
    """Test get task with invalid task_id format."""
    # Arrange
    mock_use_case.execute.side_effect = ValueError("Invalid TaskId format")
    request = planning_pb2.GetTaskRequest(task_id="")

    # Act
    response = await get_task_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is False
    assert "Internal error" in response.message
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)


@pytest.mark.asyncio
async def test_get_task_success_with_all_fields(mock_use_case, mock_context):
    """Test getting task successfully with all fields populated."""
    # Arrange
    now = datetime.now(UTC)
    full_task = Task(
        task_id=TaskId("TASK-FULL"),
        story_id=StoryId("STORY-FULL"),
        plan_id=PlanId("PLAN-FULL"),
        title="Full Task",
        description="Full description",
        type=TaskType.FEATURE,
        status=TaskStatus.IN_PROGRESS,
        assigned_to="DEV",
        estimated_hours=8,
        priority=2,
        created_at=now,
        updated_at=now,
    )
    mock_use_case.execute.return_value = full_task
    request = planning_pb2.GetTaskRequest(task_id="TASK-FULL")

    # Act
    response = await get_task_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    assert response.message == "Task found"
    assert response.task.task_id == "TASK-FULL"
    assert response.task.story_id == "STORY-FULL"
    assert response.task.plan_id == "PLAN-FULL"
    assert response.task.title == "Full Task"
    assert response.task.description == "Full description"
    assert response.task.type == "feature"
    assert response.task.status == "in_progress"
    assert response.task.assigned_to == "DEV"
    assert response.task.estimated_hours == 8
    assert response.task.priority == 2


@pytest.mark.asyncio
async def test_get_task_success_without_plan(mock_use_case, mock_context):
    """Test getting task successfully without plan_id."""
    # Arrange
    now = datetime.now(UTC)
    task_no_plan = Task(
        task_id=TaskId("TASK-NO-PLAN"),
        story_id=StoryId("STORY-NO-PLAN"),
        plan_id=None,
        title="Task without plan",
        description="",
        type=TaskType.BUG_FIX,
        status=TaskStatus.TODO,
        created_at=now,
        updated_at=now,
    )
    mock_use_case.execute.return_value = task_no_plan
    request = planning_pb2.GetTaskRequest(task_id="TASK-NO-PLAN")

    # Act
    response = await get_task_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    assert response.task.task_id == "TASK-NO-PLAN"
    assert response.task.story_id == "STORY-NO-PLAN"
    assert response.task.plan_id == ""  # Empty string when None

