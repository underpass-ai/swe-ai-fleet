"""Tests for list_tasks handler."""

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
from planning.infrastructure.grpc.handlers.list_tasks_handler import list_tasks


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
    now = datetime.now(timezone.utc)
    return [
        Task(
            task_id=TaskId("TASK-001"),
            plan_id=PlanId("PLAN-001"),
            story_id=StoryId("STORY-001"),
            title="Task 1",
            description="Description 1",
            type=TaskType.DEVELOPMENT,
            status=TaskStatus.TODO,
            created_at=now,
            updated_at=now,
        ),
        Task(
            task_id=TaskId("TASK-002"),
            plan_id=PlanId("PLAN-001"),
            story_id=StoryId("STORY-001"),
            title="Task 2",
            description="Description 2",
            type=TaskType.TESTING,
            status=TaskStatus.IN_PROGRESS,
            created_at=now,
            updated_at=now,
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
    response = await list_tasks(request, mock_context, mock_use_case)

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
    response = await list_tasks(request, mock_context, mock_use_case)

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
    response = await list_tasks(request, mock_context, mock_use_case)

    # Assert
    assert response.success is False
    assert "Error:" in response.message
    assert len(response.tasks) == 0
    mock_context.set_code.assert_called_once()

