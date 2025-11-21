"""Tests for list_projects handler."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from planning.gen import planning_pb2

from planning.domain.entities.project import Project
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.domain.value_objects.statuses.project_status import ProjectStatus
from planning.infrastructure.grpc.handlers.list_projects_handler import (
    list_projects_handler,
)


@pytest.fixture
def mock_use_case():
    """Create mock ListProjectsUseCase."""
    return AsyncMock()


@pytest.fixture
def mock_context():
    """Create mock gRPC context."""
    return Mock()


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
async def test_list_projects_success(mock_use_case, mock_context, sample_projects):
    """Test listing projects successfully."""
    # Arrange
    mock_use_case.execute.return_value = sample_projects
    request = planning_pb2.ListProjectsRequest(limit=10, offset=0)

    # Act
    response = await list_projects_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    assert "Found 2 projects" in response.message
    assert len(response.projects) == 2
    assert response.total_count == 2
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_projects_empty(mock_use_case, mock_context):
    """Test listing projects when none exist."""
    # Arrange
    mock_use_case.execute.return_value = []
    request = planning_pb2.ListProjectsRequest()

    # Act
    response = await list_projects_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    assert len(response.projects) == 0
    assert response.total_count == 0


@pytest.mark.asyncio
async def test_list_projects_error(mock_use_case, mock_context):
    """Test listing projects when an error occurs."""
    # Arrange
    mock_use_case.execute.side_effect = Exception("Database error")
    request = planning_pb2.ListProjectsRequest()

    # Act
    response = await list_projects_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is False
    assert "Error:" in response.message
    assert len(response.projects) == 0
    mock_context.set_code.assert_called_once()

