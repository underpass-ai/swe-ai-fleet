"""Tests for create_task handler."""

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
from planning.infrastructure.grpc.handlers.create_task_handler import (
    create_task_handler,
)


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
    response = await create_task_handler(request, mock_context, mock_use_case)

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
    response = await create_task_handler(request, mock_context, mock_use_case)

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
    response = await create_task_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is False
    assert "Internal error" in response.message
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)


@pytest.mark.asyncio
async def test_create_task_without_plan_id(mock_use_case, mock_context):
    """Test creating task without plan_id (optional)."""
    # Arrange
    now = datetime.now(UTC)
    task_no_plan = Task(
        task_id=TaskId("TASK-NO-PLAN"),
        story_id=StoryId("STORY-001"),
        plan_id=None,
        title="Task without plan",
        created_at=now,
        updated_at=now,
    )
    mock_use_case.execute.return_value = task_no_plan
    request = planning_pb2.CreateTaskRequest(
        story_id="STORY-001",
        # plan_id not provided (empty string)
        title="Task without plan",
        description="Description",
        type=TaskType.DEVELOPMENT.value,
    )

    # Act
    response = await create_task_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    assert response.task.task_id == "TASK-NO-PLAN"
    assert response.task.plan_id == ""  # Empty string when None
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_task_with_defaults(mock_use_case, mock_context):
    """Test creating task with default values (type, priority, estimated_hours)."""
    # Arrange
    now = datetime.now(UTC)
    task_defaults = Task(
        task_id=TaskId("TASK-DEFAULTS"),
        story_id=StoryId("STORY-001"),
        plan_id=None,
        title="Task with defaults",
        created_at=now,
        updated_at=now,
        type=TaskType.DEVELOPMENT,  # Default
        estimated_hours=0,  # Default
        priority=1,  # Default
    )
    mock_use_case.execute.return_value = task_defaults
    request = planning_pb2.CreateTaskRequest(
        story_id="STORY-001",
        title="Task with defaults",
        # type not provided - should default to DEVELOPMENT
        # estimated_hours not provided - should default to 0
        # priority not provided - should default to 1
    )

    # Act
    response = await create_task_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    assert response.task.task_id == "TASK-DEFAULTS"
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_task_with_empty_description_uses_title(mock_use_case, mock_context):
    """Test that empty description uses title as fallback."""
    # Arrange
    now = datetime.now(UTC)
    task = Task(
        task_id=TaskId("TASK-DESC"),
        story_id=StoryId("STORY-001"),
        plan_id=None,
        title="Task Title",
        description="Task Title",  # Should use title when description empty
        created_at=now,
        updated_at=now,
    )
    mock_use_case.execute.return_value = task
    request = planning_pb2.CreateTaskRequest(
        story_id="STORY-001",
        title="Task Title",
        description="",  # Empty - should use title
        type=TaskType.DEVELOPMENT.value,
    )

    # Act
    response = await create_task_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    # Verify that use case was called with description = title
    call_args = mock_use_case.execute.call_args[0][0]
    assert call_args.description.value == "Task Title"


@pytest.mark.asyncio
async def test_create_task_backward_compatibility_shim(mock_use_case, mock_context, sample_task):
    """Test backward compatibility shim function."""
    from planning.infrastructure.grpc.handlers.create_task_handler import create_task

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
    assert response.task.task_id == "TASK-001"

