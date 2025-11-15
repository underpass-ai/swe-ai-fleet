"""Tests for get_project handler."""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timezone

from planning.domain.entities.project import Project
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.domain.value_objects.statuses.project_status import ProjectStatus
from planning.gen import planning_pb2
from planning.infrastructure.grpc.handlers.get_project_handler import (
    get_project_handler,
)


@pytest.fixture
def mock_use_case():
    """Create mock GetProjectUseCase."""
    return AsyncMock()


@pytest.fixture
def mock_context():
    """Create mock gRPC context."""
    return Mock()


@pytest.fixture
def sample_project():
    """Create a sample project for testing."""
    now = datetime.now(timezone.utc)
    return Project(
        project_id=ProjectId("PROJ-001"),
        name="Test Project",
        description="Test description",
        status=ProjectStatus.ACTIVE,
        owner="test_owner",
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_get_project_success(mock_use_case, mock_context, sample_project):
    """Test getting project successfully."""
    # Arrange
    mock_use_case.execute.return_value = sample_project
    request = planning_pb2.GetProjectRequest(project_id="PROJ-001")

    # Act
    response = await get_project_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.project.project_id == "PROJ-001"
    assert response.project.name == "Test Project"
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_project_not_found(mock_use_case, mock_context):
    """Test getting project that doesn't exist."""
    # Arrange
    mock_use_case.execute.return_value = None
    request = planning_pb2.GetProjectRequest(project_id="NONEXISTENT")

    # Act
    response = await get_project_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.project.project_id == ""  # Empty project
    mock_context.set_code.assert_called_once()


@pytest.mark.asyncio
async def test_get_project_internal_error(mock_use_case, mock_context):
    """Test get project with internal error."""
    # Arrange
    mock_use_case.execute.side_effect = Exception("Database error")
    request = planning_pb2.GetProjectRequest(project_id="PROJ-001")

    # Act
    response = await get_project_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.project.project_id == ""  # Empty project on error
    mock_context.set_code.assert_called_once()

