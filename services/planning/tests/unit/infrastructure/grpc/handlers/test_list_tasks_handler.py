"""Tests for list_tasks handler."""

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
from planning.infrastructure.grpc.handlers.list_tasks_handler import (
    list_tasks_handler,
)


@pytest.fixture
def mock_use_case():
    """Create mock ListTasksUseCase."""
    return AsyncMock()


@pytest.fixture
def mock_context():
    """Create mock gRPC context."""
    return Mock()


@pytest.fixture
def sample_tasks():
    """Create sample tasks for testing."""
    now = datetime.now(UTC)
    return [
        Task(
            task_id=TaskId("TASK-001"),
            story_id=StoryId("STORY-001"),
            title="Task 1",
            created_at=now,
            updated_at=now,
            plan_id=PlanId("PLAN-001"),
            description="Description 1",
            type=TaskType.DEVELOPMENT,
            status=TaskStatus.TODO,
        ),
        Task(
            task_id=TaskId("TASK-002"),
            story_id=StoryId("STORY-001"),
            title="Task 2",
            created_at=now,
            updated_at=now,
            plan_id=PlanId("PLAN-001"),
            description="Description 2",
            type=TaskType.TESTING,
            status=TaskStatus.IN_PROGRESS,
        ),
    ]


@pytest.mark.asyncio
async def test_list_tasks_success(mock_use_case, mock_context, sample_tasks):
    """Test listing tasks successfully."""
    # Arrange
    mock_use_case.execute.return_value = sample_tasks
    request = planning_pb2.ListTasksRequest(
        story_id="STORY-001",
        limit=10,
        offset=0,
    )

    # Act
    response = await list_tasks_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    assert "Found 2 tasks" in response.message
    assert len(response.tasks) == 2
    assert response.total_count == 2
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_tasks_empty(mock_use_case, mock_context):
    """Test listing tasks when none exist."""
    # Arrange
    mock_use_case.execute.return_value = []
    request = planning_pb2.ListTasksRequest()

    # Act
    response = await list_tasks_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    assert len(response.tasks) == 0
    assert response.total_count == 0


@pytest.mark.asyncio
async def test_list_tasks_error(mock_use_case, mock_context):
    """Test listing tasks when an error occurs."""
    # Arrange
    mock_use_case.execute.side_effect = Exception("Database error")
    request = planning_pb2.ListTasksRequest()

    # Act
    response = await list_tasks_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is False
    assert "Error:" in response.message
    assert len(response.tasks) == 0
    assert response.total_count == 0
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)


@pytest.mark.asyncio
async def test_list_tasks_with_story_id(mock_use_case, mock_context, sample_tasks):
    """Test listing tasks filtered by story_id."""
    # Arrange
    mock_use_case.execute.return_value = sample_tasks
    request = planning_pb2.ListTasksRequest(
        story_id="STORY-001",
        limit=10,
        offset=0,
    )

    # Act
    response = await list_tasks_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    assert len(response.tasks) == 2
    assert response.total_count == 2
    mock_use_case.execute.assert_awaited_once_with(
        story_id=StoryId("STORY-001"),
        plan_id=None,
        limit=10,
        offset=0,
    )


@pytest.mark.asyncio
async def test_list_tasks_without_story_id(mock_use_case, mock_context, sample_tasks):
    """Test listing all tasks without story_id filter."""
    # Arrange
    mock_use_case.execute.return_value = sample_tasks
    request = planning_pb2.ListTasksRequest(
        story_id="",
        limit=100,
        offset=0,
    )

    # Act
    response = await list_tasks_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    assert len(response.tasks) == 2
    mock_use_case.execute.assert_awaited_once_with(
        story_id=None,
        plan_id=None,
        limit=100,
        offset=0,
    )


@pytest.mark.asyncio
async def test_list_tasks_limit_and_offset(mock_use_case, mock_context):
    """Test listing tasks with limit and offset."""
    # Arrange
    now = datetime.now(UTC)
    tasks = [
        Task(
            task_id=TaskId(f"TASK-{i}"),
            story_id=StoryId("STORY-001"),
            title=f"Task {i}",
            created_at=now,
            updated_at=now,
        )
        for i in range(5)
    ]
    mock_use_case.execute.return_value = tasks[:3]  # Return 3 tasks
    request = planning_pb2.ListTasksRequest(
        story_id="STORY-001",
        limit=3,
        offset=0,
    )

    # Act
    response = await list_tasks_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    assert len(response.tasks) == 3
    assert response.total_count == 3
    mock_use_case.execute.assert_awaited_once_with(
        story_id=StoryId("STORY-001"),
        plan_id=None,
        limit=3,
        offset=0,
    )


@pytest.mark.asyncio
async def test_list_tasks_invalid_limit_defaults_to_100(mock_use_case, mock_context):
    """Test that invalid limit (< 0) defaults to 100."""
    # Arrange
    mock_use_case.execute.return_value = []
    request = planning_pb2.ListTasksRequest(
        story_id="",
        limit=-5,  # Invalid limit
        offset=0,
    )

    # Act
    response = await list_tasks_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    mock_use_case.execute.assert_awaited_once_with(
        story_id=None,
        plan_id=None,
        limit=100,  # Should default to 100
        offset=0,
    )


@pytest.mark.asyncio
async def test_list_tasks_invalid_offset_defaults_to_0(mock_use_case, mock_context):
    """Test that invalid offset (< 0) defaults to 0."""
    # Arrange
    mock_use_case.execute.return_value = []
    request = planning_pb2.ListTasksRequest(
        story_id="",
        limit=10,
        offset=-10,  # Invalid offset
    )

    # Act
    response = await list_tasks_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    mock_use_case.execute.assert_awaited_once_with(
        story_id=None,
        plan_id=None,
        limit=10,
        offset=0,  # Should default to 0
    )

