"""Tests for list_stories handler."""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timezone

from planning.domain.entities.story import Story
from planning.domain.value_objects.dor_score import DORScore
from planning.domain.value_objects.epic_id import EpicId
from planning.domain.value_objects.story_id import StoryId
from planning.domain.value_objects.story_state import StoryState, StoryStateEnum
from planning.gen import planning_pb2
from planning.infrastructure.grpc.handlers.list_stories_handler import list_stories


@pytest.fixture
def mock_use_case():
    """Create mock ListStoriesUseCase."""
    return AsyncMock()


@pytest.fixture
def mock_context():
    """Create mock gRPC context."""
    return Mock()


@pytest.fixture
def sample_story():
    """Create a sample story for testing."""
    now = datetime.now(timezone.utc)
    return Story(
        story_id=StoryId("STORY-001"),
        epic_id=EpicId("EPIC-001"),
        title="Test Story",
        brief="Test brief",
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(85.0),
        created_by="test_user",
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_list_stories_success(mock_use_case, mock_context, sample_story):
    """Test listing stories successfully."""
    # Arrange
    mock_use_case.execute.return_value = [sample_story]
    request = planning_pb2.ListStoriesRequest(
        state_filter="",
        limit=10,
        offset=0,
    )

    # Act
    response = await list_stories(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    assert "Found 1 stories" in response.message
    assert len(response.stories) == 1
    assert response.total_count == 1
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_stories_with_filter(mock_use_case, mock_context, sample_story):
    """Test listing stories with state filter."""
    # Arrange
    mock_use_case.execute.return_value = [sample_story]
    request = planning_pb2.ListStoriesRequest(
        state_filter=StoryStateEnum.DRAFT.value,
        limit=10,
        offset=0,
    )

    # Act
    response = await list_stories(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    assert len(response.stories) == 1
    # Verify the use case was called with the correct filter
    call_args = mock_use_case.execute.call_args
    assert call_args.kwargs["state_filter"] is not None


@pytest.mark.asyncio
async def test_list_stories_empty(mock_use_case, mock_context):
    """Test listing stories when none exist."""
    # Arrange
    mock_use_case.execute.return_value = []
    request = planning_pb2.ListStoriesRequest()

    # Act
    response = await list_stories(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    assert len(response.stories) == 0
    assert response.total_count == 0


@pytest.mark.asyncio
async def test_list_stories_error(mock_use_case, mock_context):
    """Test listing stories when an error occurs."""
    # Arrange
    mock_use_case.execute.side_effect = Exception("Database error")
    request = planning_pb2.ListStoriesRequest()

    # Act
    response = await list_stories(request, mock_context, mock_use_case)

    # Assert
    assert response.success is False
    assert "Error:" in response.message
    assert len(response.stories) == 0
    mock_context.set_code.assert_called_once()

