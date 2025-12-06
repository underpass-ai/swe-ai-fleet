"""Tests for create_backlog_review_ceremony_handler."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from planning.application.usecases.create_backlog_review_ceremony_usecase import (
    CreateBacklogReviewCeremonyUseCase,
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
from planning.infrastructure.grpc.handlers.create_backlog_review_ceremony_handler import (
    create_backlog_review_ceremony_handler,
)


@pytest.fixture
def mock_use_case():
    """Create mock CreateBacklogReviewCeremonyUseCase."""
    return AsyncMock(spec=CreateBacklogReviewCeremonyUseCase)


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
        status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.DRAFT),
        created_at=now,
        updated_at=now,
        started_at=None,
        completed_at=None,
        review_results=(),
    )


@pytest.mark.asyncio
async def test_create_backlog_review_ceremony_success(
    mock_use_case, mock_context, sample_ceremony
):
    """Test creating backlog review ceremony successfully."""
    # Arrange
    mock_use_case.execute.return_value = sample_ceremony
    request = planning_pb2.CreateBacklogReviewCeremonyRequest(
        created_by="architect",
        story_ids=["story-1", "story-2"],
    )

    # Act
    response = await create_backlog_review_ceremony_handler(
        request, mock_context, mock_use_case
    )

    # Assert
    assert isinstance(response, planning_pb2.CreateBacklogReviewCeremonyResponse)
    assert response.success is True
    assert response.message == "Ceremony created: ceremony-123"
    assert response.ceremony.ceremony_id == "ceremony-123"
    assert len(response.ceremony.story_ids) == 2
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_backlog_review_ceremony_validation_error(
    mock_use_case, mock_context
):
    """Test creating ceremony with validation error (empty created_by)."""
    # Arrange
    # ValueError will be raised when creating UserName with empty string (line 27)
    request = planning_pb2.CreateBacklogReviewCeremonyRequest(
        created_by="",
        story_ids=[],
    )

    # Act
    response = await create_backlog_review_ceremony_handler(
        request, mock_context, mock_use_case
    )

    # Assert
    assert isinstance(response, planning_pb2.CreateBacklogReviewCeremonyResponse)
    assert response.success is False
    assert response.message == "UserName cannot be empty"
    assert not response.HasField("ceremony")
    mock_context.set_code.assert_called_once()
    # Use case should not be called if validation fails before
    mock_use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_backlog_review_ceremony_internal_error(
    mock_use_case, mock_context
):
    """Test create ceremony with internal error."""
    # Arrange
    mock_use_case.execute.side_effect = Exception("Database error")
    request = planning_pb2.CreateBacklogReviewCeremonyRequest(
        created_by="architect",
        story_ids=["story-1"],
    )

    # Act
    response = await create_backlog_review_ceremony_handler(
        request, mock_context, mock_use_case
    )

    # Assert
    assert isinstance(response, planning_pb2.CreateBacklogReviewCeremonyResponse)
    assert response.success is False
    assert "Internal error:" in response.message
    assert "Database error" in response.message
    assert not response.HasField("ceremony")
    mock_context.set_code.assert_called_once()
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_backlog_review_ceremony_no_stories(
    mock_use_case, mock_context, sample_ceremony
):
    """Test creating ceremony without initial stories."""
    # Arrange
    ceremony_no_stories = BacklogReviewCeremony(
        ceremony_id=sample_ceremony.ceremony_id,
        created_by=sample_ceremony.created_by,
        story_ids=(),  # Empty tuple
        status=sample_ceremony.status,
        created_at=sample_ceremony.created_at,
        updated_at=sample_ceremony.updated_at,
        started_at=None,
        completed_at=None,
        review_results=(),
    )
    mock_use_case.execute.return_value = ceremony_no_stories
    request = planning_pb2.CreateBacklogReviewCeremonyRequest(
        created_by="architect",
        story_ids=[],  # Empty list
    )

    # Act
    response = await create_backlog_review_ceremony_handler(
        request, mock_context, mock_use_case
    )

    # Assert
    assert isinstance(response, planning_pb2.CreateBacklogReviewCeremonyResponse)
    assert response.success is True
    assert len(response.ceremony.story_ids) == 0
    mock_use_case.execute.assert_awaited_once()

