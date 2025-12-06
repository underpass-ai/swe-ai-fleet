"""Tests for start_backlog_review_ceremony_handler."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from planning.application.usecases import CeremonyNotFoundError
from planning.application.usecases.start_backlog_review_ceremony_usecase import (
    StartBacklogReviewCeremonyUseCase,
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
from planning.infrastructure.grpc.handlers.start_backlog_review_ceremony_handler import (
    start_backlog_review_ceremony_handler,
)


@pytest.fixture
def mock_use_case():
    """Create mock StartBacklogReviewCeremonyUseCase."""
    return AsyncMock(spec=StartBacklogReviewCeremonyUseCase)


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
        created_by=UserName("po-user"),
        story_ids=(StoryId("story-1"), StoryId("story-2")),
        status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.IN_PROGRESS),
        created_at=now,
        updated_at=now,
        started_at=now,
        completed_at=None,
        review_results=(),
    )


@pytest.mark.asyncio
async def test_start_backlog_review_ceremony_success(
    mock_use_case, mock_context, sample_ceremony
):
    """Test starting backlog review ceremony successfully."""
    # Arrange
    mock_use_case.execute.return_value = (sample_ceremony, 6)
    request = planning_pb2.StartBacklogReviewCeremonyRequest(
        ceremony_id="ceremony-123",
        started_by="po-user",
    )

    # Act
    response = await start_backlog_review_ceremony_handler(
        request, mock_context, mock_use_case
    )

    # Assert
    assert isinstance(response, planning_pb2.StartBacklogReviewCeremonyResponse)
    assert response.success is True
    assert response.message == "Ceremony started: 6 deliberations submitted"
    assert response.ceremony.ceremony_id == "ceremony-123"
    assert response.total_deliberations_submitted == 6
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_backlog_review_ceremony_partial_failures(
    mock_use_case, mock_context, sample_ceremony
):
    """Test starting ceremony with some deliberations failing."""
    # Arrange
    # 2 stories * 3 roles = 6 expected, but only 4 succeeded
    mock_use_case.execute.return_value = (sample_ceremony, 4)
    request = planning_pb2.StartBacklogReviewCeremonyRequest(
        ceremony_id="ceremony-123",
        started_by="po-user",
    )

    # Act
    response = await start_backlog_review_ceremony_handler(
        request, mock_context, mock_use_case
    )

    # Assert
    assert isinstance(response, planning_pb2.StartBacklogReviewCeremonyResponse)
    assert response.success is True
    assert response.total_deliberations_submitted == 4
    assert response.ceremony.ceremony_id == "ceremony-123"
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_backlog_review_ceremony_not_found(mock_use_case, mock_context):
    """Test starting ceremony that doesn't exist."""
    # Arrange
    mock_use_case.execute.side_effect = CeremonyNotFoundError(
        "Ceremony not found: nonexistent"
    )
    request = planning_pb2.StartBacklogReviewCeremonyRequest(
        ceremony_id="nonexistent",
        started_by="po-user",
    )

    # Act
    response = await start_backlog_review_ceremony_handler(
        request, mock_context, mock_use_case
    )

    # Assert
    assert isinstance(response, planning_pb2.StartBacklogReviewCeremonyResponse)
    assert response.success is False
    assert "Ceremony not found" in response.message
    assert not response.HasField("ceremony")
    assert response.total_deliberations_submitted == 0
    mock_context.set_code.assert_called_once()
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_backlog_review_ceremony_validation_error(
    mock_use_case, mock_context
):
    """Test starting ceremony with validation error (no stories)."""
    # Arrange
    mock_use_case.execute.side_effect = ValueError(
        "Cannot start ceremony: No stories to review"
    )
    request = planning_pb2.StartBacklogReviewCeremonyRequest(
        ceremony_id="ceremony-123",
        started_by="po-user",
    )

    # Act
    response = await start_backlog_review_ceremony_handler(
        request, mock_context, mock_use_case
    )

    # Assert
    assert isinstance(response, planning_pb2.StartBacklogReviewCeremonyResponse)
    assert response.success is False
    assert "Cannot start ceremony: No stories to review" in response.message
    assert not response.HasField("ceremony")
    mock_context.set_code.assert_called_once()
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_backlog_review_ceremony_internal_error(
    mock_use_case, mock_context
):
    """Test start ceremony with internal error."""
    # Arrange
    mock_use_case.execute.side_effect = Exception("Orchestrator unreachable")
    request = planning_pb2.StartBacklogReviewCeremonyRequest(
        ceremony_id="ceremony-123",
        started_by="po-user",
    )

    # Act
    response = await start_backlog_review_ceremony_handler(
        request, mock_context, mock_use_case
    )

    # Assert
    assert isinstance(response, planning_pb2.StartBacklogReviewCeremonyResponse)
    assert response.success is False
    assert "Internal error:" in response.message
    assert "Orchestrator unreachable" in response.message
    assert not response.HasField("ceremony")
    mock_context.set_code.assert_called_once()
    mock_use_case.execute.assert_awaited_once()

