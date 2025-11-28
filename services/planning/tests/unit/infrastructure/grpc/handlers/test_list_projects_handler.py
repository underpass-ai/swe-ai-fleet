"""Unit tests for list_projects_handler."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
import grpc
from planning.application.usecases.list_projects_usecase import ListProjectsUseCase
from planning.domain.entities.project import Project
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.domain.value_objects.statuses.project_status import ProjectStatus
from planning.gen import planning_pb2
from planning.infrastructure.grpc.handlers.list_projects_handler import list_projects_handler


@pytest.fixture
def mock_use_case():
    """Create mock ListProjectsUseCase."""
    return AsyncMock(spec=ListProjectsUseCase)


@pytest.fixture
def mock_context():
    """Create mock gRPC context."""
    context = AsyncMock()
    context.set_code = AsyncMock()
    return context


@pytest.fixture
def sample_projects():
    """Create sample projects for testing."""
    now = datetime.now(UTC)
    return [
        Project(
            project_id=ProjectId("PROJ-001"),
            name="Project 1",
            description="Description 1",
            status=ProjectStatus.ACTIVE,
            owner="owner1",
            created_at=now,
            updated_at=now,
        ),
        Project(
            project_id=ProjectId("PROJ-002"),
            name="Project 2",
            description="Description 2",
            status=ProjectStatus.COMPLETED,
            owner="owner2",
            created_at=now,
            updated_at=now,
        ),
    ]


@pytest.mark.asyncio
async def test_list_projects_handler_success(mock_use_case, mock_context, sample_projects):
    """Test successful list_projects handler call."""
    # Arrange
    mock_use_case.execute.return_value = sample_projects
    request = planning_pb2.ListProjectsRequest(limit=10, offset=0)

    # Act
    response = await list_projects_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    assert len(response.projects) == 2
    assert "Found 2 projects" in response.message
    mock_use_case.execute.assert_awaited_once_with(
        status_filter=None,
        limit=10,
        offset=0,
    )


@pytest.mark.asyncio
async def test_list_projects_handler_default_parameters(mock_use_case, mock_context, sample_projects):
    """Test list_projects handler with default parameters."""
    # Arrange
    mock_use_case.execute.return_value = sample_projects
    request = planning_pb2.ListProjectsRequest()  # No limit/offset

    # Act
    response = await list_projects_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    mock_use_case.execute.assert_awaited_once_with(
        status_filter=None,
        limit=100,  # Default
        offset=0,   # Default
    )


@pytest.mark.asyncio
async def test_list_projects_handler_with_status_filter(mock_use_case, mock_context, sample_projects):
    """Test list_projects handler with status filter."""
    # Arrange
    filtered_projects = [p for p in sample_projects if p.status == ProjectStatus.COMPLETED]
    mock_use_case.execute.return_value = filtered_projects
    request = planning_pb2.ListProjectsRequest(
        status_filter="completed",
        limit=10,
        offset=0,
    )

    # Act
    response = await list_projects_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    assert len(response.projects) == 1
    mock_use_case.execute.assert_awaited_once_with(
        status_filter=ProjectStatus.COMPLETED,
        limit=10,
        offset=0,
    )


@pytest.mark.asyncio
async def test_list_projects_handler_invalid_status_filter(mock_use_case, mock_context):
    """Test list_projects handler rejects invalid status filter."""
    # Arrange
    request = planning_pb2.ListProjectsRequest(
        status_filter="invalid_status",
        limit=10,
        offset=0,
    )

    # Act
    response = await list_projects_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is False
    assert "Invalid status_filter" in response.message
    assert len(response.projects) == 0
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)
    mock_use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_projects_handler_empty_status_filter(mock_use_case, mock_context, sample_projects):
    """Test list_projects handler with empty status filter (treated as None)."""
    # Arrange
    mock_use_case.execute.return_value = sample_projects
    request = planning_pb2.ListProjectsRequest(
        status_filter="",  # Empty string
        limit=10,
        offset=0,
    )

    # Act
    response = await list_projects_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    mock_use_case.execute.assert_awaited_once_with(
        status_filter=None,  # Empty string treated as None
        limit=10,
        offset=0,
    )


@pytest.mark.asyncio
async def test_list_projects_handler_all_status_values(mock_use_case, mock_context):
    """Test list_projects handler accepts all valid status values."""
    # Arrange
    valid_statuses = [
        "active",
        "planning",
        "in_progress",
        "completed",
        "archived",
        "cancelled",
    ]

    for status_str in valid_statuses:
        mock_use_case.execute.return_value = []
        request = planning_pb2.ListProjectsRequest(
            status_filter=status_str,
            limit=10,
            offset=0,
        )

        # Act
        response = await list_projects_handler(request, mock_context, mock_use_case)

        # Assert
        assert response.success is True
        mock_context.set_code.assert_not_called()

    # Reset mock
    mock_context.reset_mock()


@pytest.mark.asyncio
async def test_list_projects_handler_invalid_limit_uses_default(mock_use_case, mock_context, sample_projects):
    """Test list_projects handler uses default limit when limit <= 0."""
    # Arrange
    mock_use_case.execute.return_value = sample_projects
    request = planning_pb2.ListProjectsRequest(limit=0, offset=0)  # Invalid limit

    # Act
    response = await list_projects_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    mock_use_case.execute.assert_awaited_once_with(
        status_filter=None,
        limit=100,  # Default used
        offset=0,
    )


@pytest.mark.asyncio
async def test_list_projects_handler_invalid_offset_uses_default(mock_use_case, mock_context, sample_projects):
    """Test list_projects handler uses default offset when offset < 0."""
    # Arrange
    mock_use_case.execute.return_value = sample_projects
    request = planning_pb2.ListProjectsRequest(limit=10, offset=-1)  # Invalid offset

    # Act
    response = await list_projects_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    mock_use_case.execute.assert_awaited_once_with(
        status_filter=None,
        limit=10,
        offset=0,  # Default used
    )


@pytest.mark.asyncio
async def test_list_projects_handler_empty_result(mock_use_case, mock_context):
    """Test list_projects handler with empty result."""
    # Arrange
    mock_use_case.execute.return_value = []
    request = planning_pb2.ListProjectsRequest(limit=10, offset=0)

    # Act
    response = await list_projects_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    assert len(response.projects) == 0
    assert "Found 0 projects" in response.message


@pytest.mark.asyncio
async def test_list_projects_handler_use_case_error(mock_use_case, mock_context):
    """Test list_projects handler handles use case errors."""
    # Arrange
    mock_use_case.execute.side_effect = Exception("Database connection error")
    request = planning_pb2.ListProjectsRequest(limit=10, offset=0)

    # Act
    response = await list_projects_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is False
    assert "Error" in response.message
    assert len(response.projects) == 0
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)
