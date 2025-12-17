"""Tests for list_backlog_review_ceremonies_handler."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from planning.application.usecases.list_backlog_review_ceremonies_usecase import (
    ListBacklogReviewCeremoniesUseCase,
)
from planning.domain.entities.backlog_review_ceremony import BacklogReviewCeremony
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.statuses.backlog_review_ceremony_status import (
    BacklogReviewCeremonyStatus,
    BacklogReviewCeremonyStatusEnum,
)
from planning.gen import planning_pb2
from planning.infrastructure.grpc.handlers.list_backlog_review_ceremonies_handler import (
    list_backlog_review_ceremonies_handler,
)


@pytest.fixture
def mock_use_case():
    """Create mock ListBacklogReviewCeremoniesUseCase."""
    return AsyncMock(spec=ListBacklogReviewCeremoniesUseCase)


@pytest.fixture
def mock_context():
    """Create mock gRPC context."""
    return Mock()


@pytest.fixture
def sample_ceremonies():
    """Create sample ceremonies for testing."""
    base_time = datetime.now(UTC)
    return [
        BacklogReviewCeremony(
            ceremony_id=BacklogReviewCeremonyId("BRC-001"),
            created_by=UserName("po1@example.com"),
            story_ids=(),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.DRAFT),
            created_at=base_time,
            updated_at=base_time,
        ),
        BacklogReviewCeremony(
            ceremony_id=BacklogReviewCeremonyId("BRC-002"),
            created_by=UserName("po2@example.com"),
            story_ids=(),
            status=BacklogReviewCeremonyStatus(
                BacklogReviewCeremonyStatusEnum.IN_PROGRESS
            ),
            created_at=base_time,
            updated_at=base_time,
            started_at=base_time,
        ),
    ]


@pytest.mark.asyncio
async def test_list_ceremonies_success(mock_use_case, mock_context, sample_ceremonies):
    """Test listing ceremonies successfully."""
    # Arrange
    mock_use_case.execute.return_value = sample_ceremonies
    request = planning_pb2.ListBacklogReviewCeremoniesRequest(
        limit=100, offset=0
    )

    # Act
    response = await list_backlog_review_ceremonies_handler(
        request, mock_context, mock_use_case
    )

    # Assert
    assert isinstance(response, planning_pb2.ListBacklogReviewCeremoniesResponse)
    assert response.success is True
    assert response.message == "Found 2 ceremonies"
    assert len(response.ceremonies) == 2
    assert response.total_count == 2
    assert response.ceremonies[0].ceremony_id == "BRC-001"
    assert response.ceremonies[1].ceremony_id == "BRC-002"
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_ceremonies_with_status_filter(
    mock_use_case, mock_context, sample_ceremonies
):
    """Test listing ceremonies with status filter."""
    # Arrange
    filtered = [sample_ceremonies[0]]  # Only DRAFT
    mock_use_case.execute.return_value = filtered
    request = planning_pb2.ListBacklogReviewCeremoniesRequest(
        status_filter="DRAFT", limit=100, offset=0
    )

    # Act
    response = await list_backlog_review_ceremonies_handler(
        request, mock_context, mock_use_case
    )

    # Assert
    assert response.success is True
    assert len(response.ceremonies) == 1
    assert response.ceremonies[0].ceremony_id == "BRC-001"
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_ceremonies_with_created_by_filter(
    mock_use_case, mock_context, sample_ceremonies
):
    """Test listing ceremonies with created_by filter."""
    # Arrange
    filtered = [sample_ceremonies[0]]  # Only po1@example.com
    mock_use_case.execute.return_value = filtered
    request = planning_pb2.ListBacklogReviewCeremoniesRequest(
        created_by="po1@example.com", limit=100, offset=0
    )

    # Act
    response = await list_backlog_review_ceremonies_handler(
        request, mock_context, mock_use_case
    )

    # Assert
    assert response.success is True
    assert len(response.ceremonies) == 1
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_ceremonies_empty_result(mock_use_case, mock_context):
    """Test listing when no ceremonies found."""
    # Arrange
    mock_use_case.execute.return_value = []
    request = planning_pb2.ListBacklogReviewCeremoniesRequest(
        limit=100, offset=0
    )

    # Act
    response = await list_backlog_review_ceremonies_handler(
        request, mock_context, mock_use_case
    )

    # Assert
    assert response.success is True
    assert response.message == "Found 0 ceremonies"
    assert len(response.ceremonies) == 0
    assert response.total_count == 0


@pytest.mark.asyncio
async def test_list_ceremonies_invalid_status_filter(mock_use_case, mock_context):
    """Test listing with invalid status filter."""
    # Arrange
    request = planning_pb2.ListBacklogReviewCeremoniesRequest(
        status_filter="INVALID_STATUS", limit=100, offset=0
    )

    # Act
    response = await list_backlog_review_ceremonies_handler(
        request, mock_context, mock_use_case
    )

    # Assert
    assert response.success is False
    assert "Invalid status_filter" in response.message
    assert len(response.ceremonies) == 0
    assert response.total_count == 0
    mock_context.set_code.assert_called_once()
    mock_use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_ceremonies_invalid_created_by(mock_use_case, mock_context):
    """Test listing with invalid created_by (empty string)."""
    # Arrange
    request = planning_pb2.ListBacklogReviewCeremoniesRequest(
        created_by="", limit=100, offset=0
    )

    # Act
    response = await list_backlog_review_ceremonies_handler(
        request, mock_context, mock_use_case
    )

    # Assert
    assert response.success is False
    assert "Invalid created_by" in response.message
    assert len(response.ceremonies) == 0
    assert response.total_count == 0
    mock_context.set_code.assert_called_once()
    mock_use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_ceremonies_validation_error(mock_use_case, mock_context):
    """Test listing with validation error (invalid limit)."""
    # Arrange
    mock_use_case.execute.side_effect = ValueError("limit must be >= 1")
    request = planning_pb2.ListBacklogReviewCeremoniesRequest(
        limit=0, offset=0
    )

    # Act
    response = await list_backlog_review_ceremonies_handler(
        request, mock_context, mock_use_case
    )

    # Assert
    assert response.success is False
    assert "Validation error" in response.message
    assert "limit must be >= 1" in response.message
    assert len(response.ceremonies) == 0
    assert response.total_count == 0
    mock_context.set_code.assert_called_once()


@pytest.mark.asyncio
async def test_list_ceremonies_internal_error(mock_use_case, mock_context):
    """Test listing with internal error."""
    # Arrange
    mock_use_case.execute.side_effect = Exception("Database error")
    request = planning_pb2.ListBacklogReviewCeremoniesRequest(
        limit=100, offset=0
    )

    # Act
    response = await list_backlog_review_ceremonies_handler(
        request, mock_context, mock_use_case
    )

    # Assert
    assert response.success is False
    assert "Internal error" in response.message
    assert "Database error" in response.message
    assert len(response.ceremonies) == 0
    assert response.total_count == 0
    mock_context.set_code.assert_called_once()


@pytest.mark.asyncio
async def test_list_ceremonies_default_pagination(mock_use_case, mock_context, sample_ceremonies):
    """Test listing with default pagination values."""
    # Arrange
    mock_use_case.execute.return_value = sample_ceremonies
    request = planning_pb2.ListBacklogReviewCeremoniesRequest()

    # Act
    response = await list_backlog_review_ceremonies_handler(
        request, mock_context, mock_use_case
    )

    # Assert
    assert response.success is True
    # Should use defaults: limit=100, offset=0
    mock_use_case.execute.assert_awaited_once_with(
        status_filter=None,
        created_by=None,
        limit=100,
        offset=0,
    )
