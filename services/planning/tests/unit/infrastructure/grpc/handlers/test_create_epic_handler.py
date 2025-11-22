"""Tests for create_epic handler."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from planning.domain.entities.epic import Epic
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.domain.value_objects.statuses.epic_status import EpicStatus
from planning.gen import planning_pb2
from planning.infrastructure.grpc.handlers.create_epic_handler import (
    create_epic_handler,
)


@pytest.fixture
def mock_use_case():
    """Create mock CreateEpicUseCase."""
    return AsyncMock()


@pytest.fixture
def mock_context():
    """Create mock gRPC context."""
    return Mock()


@pytest.fixture
def sample_epic():
    """Create a sample epic for testing."""
    now = datetime.now(UTC)
    return Epic(
        epic_id=EpicId("EPIC-001"),
        project_id=ProjectId("PROJ-001"),
        title="Test Epic",
        description="Test description",
        status=EpicStatus.PLANNING,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_create_epic_success(mock_use_case, mock_context, sample_epic):
    """Test creating epic successfully."""
    # Arrange
    mock_use_case.execute.return_value = sample_epic
    request = planning_pb2.CreateEpicRequest(
        project_id="PROJ-001",
        title="Test Epic",
        description="Test description",
    )

    # Act
    response = await create_epic_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    assert "Epic created" in response.message
    assert response.epic.epic_id == "EPIC-001"
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_epic_validation_error(mock_use_case, mock_context):
    """Test create with validation error."""
    # Arrange
    mock_use_case.execute.side_effect = ValueError("Project not found")
    request = planning_pb2.CreateEpicRequest(
        project_id="INVALID",
        title="Test",
        description="",
    )

    # Act
    response = await create_epic_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is False
    assert "Project not found" in response.message
    mock_context.set_code.assert_called_once()


@pytest.mark.asyncio
async def test_create_epic_internal_error(mock_use_case, mock_context):
    """Test create with internal error."""
    # Arrange
    mock_use_case.execute.side_effect = Exception("Database error")
    request = planning_pb2.CreateEpicRequest(
        project_id="PROJ-001",
        title="Test",
        description="Test",
    )

    # Act
    response = await create_epic_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is False
    assert "Internal error" in response.message
    mock_context.set_code.assert_called_once()

