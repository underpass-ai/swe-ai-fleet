"""Tests for create_project handler."""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timezone

from planning.domain.entities.project import Project
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.domain.value_objects.statuses.project_status import ProjectStatus
from planning.gen import planning_pb2
from planning.infrastructure.grpc.handlers.create_project_handler import (
    create_project_handler,
)


@pytest.fixture
def mock_use_case():
    """Create mock CreateProjectUseCase."""
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
async def test_create_project_success(mock_use_case, mock_context, sample_project):
    """Test creating project successfully."""
    # Arrange
    mock_use_case.execute.return_value = sample_project
    request = planning_pb2.CreateProjectRequest(
        name="Test Project",
        description="Test description",
        owner="test_owner",
    )

    # Act
    response = await create_project_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    assert "Project created" in response.message
    assert response.project.project_id == "PROJ-001"
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_project_validation_error(mock_use_case, mock_context):
    """Test create with validation error."""
    # Arrange
    mock_use_case.execute.side_effect = ValueError("Name cannot be empty")
    request = planning_pb2.CreateProjectRequest(
        name="",
        description="",
        owner="",
    )

    # Act
    response = await create_project_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is False
    assert "Name cannot be empty" in response.message
    mock_context.set_code.assert_called_once()


@pytest.mark.asyncio
async def test_create_project_internal_error(mock_use_case, mock_context):
    """Test create with internal error."""
    # Arrange
    mock_use_case.execute.side_effect = Exception("Database error")
    request = planning_pb2.CreateProjectRequest(
        name="Test",
        description="Test",
        owner="owner",
    )

    # Act
    response = await create_project_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is False
    assert "Internal error" in response.message
    mock_context.set_code.assert_called_once()

