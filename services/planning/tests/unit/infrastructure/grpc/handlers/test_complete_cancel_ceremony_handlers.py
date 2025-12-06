"""Tests for complete and cancel ceremony handlers."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from planning.application.usecases import CeremonyNotFoundError
from planning.application.usecases.cancel_backlog_review_ceremony_usecase import (
    CancelBacklogReviewCeremonyUseCase,
)
from planning.application.usecases.complete_backlog_review_ceremony_usecase import (
    CompleteBacklogReviewCeremonyUseCase,
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
from planning.infrastructure.grpc.handlers.complete_cancel_ceremony_handlers import (
    cancel_backlog_review_ceremony_handler,
    complete_backlog_review_ceremony_handler,
)


@pytest.fixture
def mock_complete_use_case():
    """Create mock CompleteBacklogReviewCeremonyUseCase."""
    return AsyncMock(spec=CompleteBacklogReviewCeremonyUseCase)


@pytest.fixture
def mock_cancel_use_case():
    """Create mock CancelBacklogReviewCeremonyUseCase."""
    return AsyncMock(spec=CancelBacklogReviewCeremonyUseCase)


@pytest.fixture
def mock_context():
    """Create mock gRPC context."""
    return Mock()


@pytest.fixture
def sample_completed_ceremony():
    """Create a sample completed ceremony."""
    now = datetime.now(UTC)
    return BacklogReviewCeremony(
        ceremony_id=BacklogReviewCeremonyId("ceremony-123"),
        created_by=UserName("po-user"),
        story_ids=(StoryId("story-1"), StoryId("story-2")),
        status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.COMPLETED),
        created_at=now,
        updated_at=now,
        started_at=now,
        completed_at=now,
        review_results=(),
    )


@pytest.fixture
def sample_cancelled_ceremony():
    """Create a sample cancelled ceremony."""
    now = datetime.now(UTC)
    return BacklogReviewCeremony(
        ceremony_id=BacklogReviewCeremonyId("ceremony-123"),
        created_by=UserName("po-user"),
        story_ids=(StoryId("story-1"),),
        status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.CANCELLED),
        created_at=now,
        updated_at=now,
        started_at=None,
        completed_at=None,
        review_results=(),
    )


# ============================================================================
# COMPLETE CEREMONY TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_complete_ceremony_success(
    mock_complete_use_case, mock_context, sample_completed_ceremony
):
    """Test completing ceremony successfully."""
    # Arrange
    mock_complete_use_case.execute.return_value = sample_completed_ceremony
    request = planning_pb2.CompleteBacklogReviewCeremonyRequest(
        ceremony_id="ceremony-123",
        completed_by="po-user",
    )

    # Act
    response = await complete_backlog_review_ceremony_handler(
        request, mock_context, mock_complete_use_case
    )

    # Assert
    assert isinstance(response, planning_pb2.CompleteBacklogReviewCeremonyResponse)
    assert response.success is True
    assert response.message == "Ceremony completed: ceremony-123"
    assert response.ceremony.ceremony_id == "ceremony-123"
    mock_complete_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_complete_ceremony_not_found(mock_complete_use_case, mock_context):
    """Test completing ceremony that doesn't exist."""
    # Arrange
    mock_complete_use_case.execute.side_effect = CeremonyNotFoundError(
        "Ceremony not found: nonexistent"
    )
    request = planning_pb2.CompleteBacklogReviewCeremonyRequest(
        ceremony_id="nonexistent",
        completed_by="po-user",
    )

    # Act
    response = await complete_backlog_review_ceremony_handler(
        request, mock_context, mock_complete_use_case
    )

    # Assert
    assert isinstance(response, planning_pb2.CompleteBacklogReviewCeremonyResponse)
    assert response.success is False
    assert "Ceremony not found" in response.message
    assert not response.HasField("ceremony")
    mock_context.set_code.assert_called_once()


@pytest.mark.asyncio
async def test_complete_ceremony_validation_error(mock_complete_use_case, mock_context):
    """Test completing ceremony with pending approvals."""
    # Arrange
    mock_complete_use_case.execute.side_effect = ValueError(
        "Cannot complete ceremony: Story story-1 still has pending approval"
    )
    request = planning_pb2.CompleteBacklogReviewCeremonyRequest(
        ceremony_id="ceremony-123",
        completed_by="po-user",
    )

    # Act
    response = await complete_backlog_review_ceremony_handler(
        request, mock_context, mock_complete_use_case
    )

    # Assert
    assert isinstance(response, planning_pb2.CompleteBacklogReviewCeremonyResponse)
    assert response.success is False
    assert "pending approval" in response.message
    assert not response.HasField("ceremony")
    mock_context.set_code.assert_called_once()


@pytest.mark.asyncio
async def test_complete_ceremony_internal_error(mock_complete_use_case, mock_context):
    """Test completing ceremony with internal error."""
    # Arrange
    mock_complete_use_case.execute.side_effect = Exception("Database error")
    request = planning_pb2.CompleteBacklogReviewCeremonyRequest(
        ceremony_id="ceremony-123",
        completed_by="po-user",
    )

    # Act
    response = await complete_backlog_review_ceremony_handler(
        request, mock_context, mock_complete_use_case
    )

    # Assert
    assert isinstance(response, planning_pb2.CompleteBacklogReviewCeremonyResponse)
    assert response.success is False
    assert "Internal error:" in response.message
    assert not response.HasField("ceremony")
    mock_context.set_code.assert_called_once()


# ============================================================================
# CANCEL CEREMONY TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_cancel_ceremony_success(
    mock_cancel_use_case, mock_context, sample_cancelled_ceremony
):
    """Test cancelling ceremony successfully."""
    # Arrange
    mock_cancel_use_case.execute.return_value = sample_cancelled_ceremony
    request = planning_pb2.CancelBacklogReviewCeremonyRequest(
        ceremony_id="ceremony-123",
        cancelled_by="po-user",
    )

    # Act
    response = await cancel_backlog_review_ceremony_handler(
        request, mock_context, mock_cancel_use_case
    )

    # Assert
    assert isinstance(response, planning_pb2.CancelBacklogReviewCeremonyResponse)
    assert response.success is True
    assert response.message == "Ceremony cancelled: ceremony-123"
    assert response.ceremony.ceremony_id == "ceremony-123"
    mock_cancel_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancel_ceremony_not_found(mock_cancel_use_case, mock_context):
    """Test cancelling ceremony that doesn't exist."""
    # Arrange
    mock_cancel_use_case.execute.side_effect = CeremonyNotFoundError(
        "Ceremony not found: nonexistent"
    )
    request = planning_pb2.CancelBacklogReviewCeremonyRequest(
        ceremony_id="nonexistent",
        cancelled_by="po-user",
    )

    # Act
    response = await cancel_backlog_review_ceremony_handler(
        request, mock_context, mock_cancel_use_case
    )

    # Assert
    assert isinstance(response, planning_pb2.CancelBacklogReviewCeremonyResponse)
    assert response.success is False
    assert "Ceremony not found" in response.message
    assert not response.HasField("ceremony")
    mock_context.set_code.assert_called_once()


@pytest.mark.asyncio
async def test_cancel_ceremony_validation_error(mock_cancel_use_case, mock_context):
    """Test cancelling completed ceremony (not allowed)."""
    # Arrange
    mock_cancel_use_case.execute.side_effect = ValueError(
        "Cannot cancel completed ceremony"
    )
    request = planning_pb2.CancelBacklogReviewCeremonyRequest(
        ceremony_id="ceremony-123",
        cancelled_by="po-user",
    )

    # Act
    response = await cancel_backlog_review_ceremony_handler(
        request, mock_context, mock_cancel_use_case
    )

    # Assert
    assert isinstance(response, planning_pb2.CancelBacklogReviewCeremonyResponse)
    assert response.success is False
    assert "Cannot cancel completed ceremony" in response.message
    assert not response.HasField("ceremony")
    mock_context.set_code.assert_called_once()


@pytest.mark.asyncio
async def test_cancel_ceremony_internal_error(mock_cancel_use_case, mock_context):
    """Test cancelling ceremony with internal error."""
    # Arrange
    mock_cancel_use_case.execute.side_effect = Exception("Database error")
    request = planning_pb2.CancelBacklogReviewCeremonyRequest(
        ceremony_id="ceremony-123",
        cancelled_by="po-user",
    )

    # Act
    response = await cancel_backlog_review_ceremony_handler(
        request, mock_context, mock_cancel_use_case
    )

    # Assert
    assert isinstance(response, planning_pb2.CancelBacklogReviewCeremonyResponse)
    assert response.success is False
    assert "Internal error:" in response.message
    assert not response.HasField("ceremony")
    mock_context.set_code.assert_called_once()

