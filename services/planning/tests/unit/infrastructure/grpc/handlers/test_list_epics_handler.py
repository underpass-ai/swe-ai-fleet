"""Tests for list_epics handler."""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timezone

from planning.domain.entities.epic import Epic
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.domain.value_objects.statuses.epic_status import EpicStatus
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.gen import planning_pb2
from planning.infrastructure.grpc.handlers.list_epics_handler import list_epics


@pytest.fixture
def mock_use_case():
    """Create mock ListEpicsUseCase."""
    return AsyncMock()


@pytest.fixture
def mock_context():
    """Create mock gRPC context."""
    return Mock()


@pytest.fixture
def sample_epics():
    """Create sample epics for testing."""
    now = datetime.now(timezone.utc)
    return [
        Epic(
            epic_id=EpicId("EPIC-001"),
            project_id=ProjectId("PROJ-001"),
            title="Epic 1",
            description="Description 1",
            status=EpicStatus.IN_PROGRESS,
            created_at=now,
            updated_at=now,
        ),
        Epic(
            epic_id=EpicId("EPIC-002"),
            project_id=ProjectId("PROJ-001"),
            title="Epic 2",
            description="Description 2",
            status=EpicStatus.PLANNING,
            created_at=now,
            updated_at=now,
        ),
    ]


@pytest.mark.asyncio
async def test_list_epics_success(mock_use_case, mock_context, sample_epics):
    """Test listing epics successfully."""
    # Arrange
    mock_use_case.execute.return_value = sample_epics
    request = planning_pb2.ListEpicsRequest(
        project_id="PROJ-001",
        limit=10,
        offset=0,
    )

    # Act
    response = await list_epics(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    assert "Found 2 epics" in response.message
    assert len(response.epics) == 2
    assert response.total_count == 2
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_epics_empty(mock_use_case, mock_context):
    """Test listing epics when none exist."""
    # Arrange
    mock_use_case.execute.return_value = []
    request = planning_pb2.ListEpicsRequest()

    # Act
    response = await list_epics(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    assert len(response.epics) == 0
    assert response.total_count == 0


@pytest.mark.asyncio
async def test_list_epics_error(mock_use_case, mock_context):
    """Test listing epics when an error occurs."""
    # Arrange
    mock_use_case.execute.side_effect = Exception("Database error")
    request = planning_pb2.ListEpicsRequest()

    # Act
    response = await list_epics(request, mock_context, mock_use_case)

    # Assert
    assert response.success is False
    assert "Error:" in response.message
    assert len(response.epics) == 0
    mock_context.set_code.assert_called_once()

