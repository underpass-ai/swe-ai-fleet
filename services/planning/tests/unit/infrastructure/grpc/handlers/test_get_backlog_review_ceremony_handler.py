"""Tests for get_backlog_review_ceremony_handler."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from planning.application.usecases.get_backlog_review_ceremony_usecase import (
    GetBacklogReviewCeremonyUseCase,
)
from planning.domain.entities.backlog_review_ceremony import BacklogReviewCeremony
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.statuses.backlog_review_ceremony_status import (
    BacklogReviewCeremonyStatus,
    BacklogReviewCeremonyStatusEnum,
)
from planning.gen import planning_pb2
from planning.infrastructure.grpc.handlers.get_backlog_review_ceremony_handler import (
    get_backlog_review_ceremony_handler,
)


@pytest.fixture
def mock_use_case():
    """Create mock GetBacklogReviewCeremonyUseCase."""
    return AsyncMock(spec=GetBacklogReviewCeremonyUseCase)


@pytest.fixture
def mock_context():
    """Create mock gRPC context."""
    return Mock()


@pytest.fixture
def sample_ceremony():
    """Create a sample ceremony for testing."""
    now = datetime.now(UTC)
    return BacklogReviewCeremony(
        ceremony_id=BacklogReviewCeremonyId("ceremony-123"),
        created_by=UserName("architect"),
        story_ids=(StoryId("story-1"), StoryId("story-2")),
        status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.IN_PROGRESS),
        created_at=now,
        updated_at=now,
        started_at=now,
        completed_at=None,
        review_results=(),
    )


@pytest.mark.asyncio
async def test_get_backlog_review_ceremony_success(
    mock_use_case, mock_context, sample_ceremony
):
    """Test getting backlog review ceremony successfully."""
    # Arrange
    mock_use_case.execute.return_value = sample_ceremony
    request = planning_pb2.GetBacklogReviewCeremonyRequest(ceremony_id="ceremony-123")

    # Act
    response = await get_backlog_review_ceremony_handler(
        request, mock_context, mock_use_case
    )

    # Assert
    assert isinstance(response, planning_pb2.BacklogReviewCeremonyResponse)
    assert response.success is True
    assert response.message == "Ceremony retrieved: ceremony-123"
    assert response.ceremony.ceremony_id == "ceremony-123"
    assert len(response.ceremony.story_ids) == 2
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_backlog_review_ceremony_not_found(mock_use_case, mock_context):
    """Test getting ceremony that doesn't exist."""
    # Arrange
    mock_use_case.execute.return_value = None
    request = planning_pb2.GetBacklogReviewCeremonyRequest(ceremony_id="nonexistent")

    # Act
    response = await get_backlog_review_ceremony_handler(
        request, mock_context, mock_use_case
    )

    # Assert
    assert isinstance(response, planning_pb2.BacklogReviewCeremonyResponse)
    assert response.success is False
    assert response.message == "Ceremony not found: nonexistent"
    assert not response.HasField("ceremony")
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_backlog_review_ceremony_internal_error(mock_use_case, mock_context):
    """Test get ceremony with internal error."""
    # Arrange
    mock_use_case.execute.side_effect = Exception("Database error")
    request = planning_pb2.GetBacklogReviewCeremonyRequest(ceremony_id="ceremony-123")

    # Act
    response = await get_backlog_review_ceremony_handler(
        request, mock_context, mock_use_case
    )

    # Assert
    assert isinstance(response, planning_pb2.BacklogReviewCeremonyResponse)
    assert response.success is False
    assert "Internal error:" in response.message
    assert "Database error" in response.message
    assert not response.HasField("ceremony")
    mock_context.set_code.assert_called_once()
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_backlog_review_ceremony_validation_error(
    mock_use_case, mock_context
):
    """Test get ceremony with invalid ceremony_id (validation error)."""
    # Arrange
    mock_use_case.execute.side_effect = ValueError("Invalid ceremony ID format")
    request = planning_pb2.GetBacklogReviewCeremonyRequest(ceremony_id="")

    # Act
    response = await get_backlog_review_ceremony_handler(
        request, mock_context, mock_use_case
    )

    # Assert
    assert isinstance(response, planning_pb2.BacklogReviewCeremonyResponse)
    assert response.success is False
    assert "Internal error:" in response.message
    assert not response.HasField("ceremony")
    mock_context.set_code.assert_called_once()

