"""Tests for get_epic handler."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from planning.gen import planning_pb2

from planning.domain.entities.epic import Epic
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.domain.value_objects.statuses.epic_status import EpicStatus
from planning.infrastructure.grpc.handlers.get_epic_handler import get_epic_handler


@pytest.fixture
def mock_use_case():
    """Create mock GetEpicUseCase."""
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
        status=EpicStatus.IN_PROGRESS,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_get_epic_success(mock_use_case, mock_context, sample_epic):
    """Test getting epic successfully."""
    # Arrange
    mock_use_case.execute.return_value = sample_epic
    request = planning_pb2.GetEpicRequest(epic_id="EPIC-001")

    # Act
    response = await get_epic_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.epic.epic_id == "EPIC-001"
    assert response.epic.title == "Test Epic"
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_epic_not_found(mock_use_case, mock_context):
    """Test getting epic that doesn't exist."""
    # Arrange
    mock_use_case.execute.return_value = None
    request = planning_pb2.GetEpicRequest(epic_id="NONEXISTENT")

    # Act
    response = await get_epic_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.epic.epic_id == ""  # Empty epic
    mock_context.set_code.assert_called_once()


@pytest.mark.asyncio
async def test_get_epic_internal_error(mock_use_case, mock_context):
    """Test get epic with internal error."""
    # Arrange
    mock_use_case.execute.side_effect = Exception("Database error")
    request = planning_pb2.GetEpicRequest(epic_id="EPIC-001")

    # Act
    response = await get_epic_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.epic.epic_id == ""  # Empty epic on error
    mock_context.set_code.assert_called_once()

