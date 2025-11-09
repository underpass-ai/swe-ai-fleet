"""Tests for get_story handler."""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timezone

from planning.domain.entities.story import Story
from planning.domain.value_objects.epic_id import EpicId
from planning.domain.value_objects.story_id import StoryId
from planning.domain.value_objects.story_state import StoryState, StoryStateEnum
from planning.gen import planning_pb2
from planning.infrastructure.grpc.handlers.get_story_handler import get_story


@pytest.fixture
def mock_storage():
    """Create mock StoragePort."""
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
        dor_score=85.0,
        created_by="test_user",
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_get_story_success(mock_storage, mock_context, sample_story):
    """Test getting story successfully."""
    # Arrange
    mock_storage.get_story.return_value = sample_story
    request = planning_pb2.GetStoryRequest(story_id="STORY-001")

    # Act
    response = await get_story(request, mock_context, mock_storage)

    # Assert
    assert response.story_id == "STORY-001"
    assert response.title == "Test Story"
    mock_storage.get_story.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_story_not_found(mock_storage, mock_context):
    """Test getting story that doesn't exist."""
    # Arrange
    mock_storage.get_story.return_value = None
    request = planning_pb2.GetStoryRequest(story_id="NONEXISTENT")

    # Act
    response = await get_story(request, mock_context, mock_storage)

    # Assert
    assert response.story_id == ""  # Empty story
    mock_context.set_code.assert_called_once()


@pytest.mark.asyncio
async def test_get_story_internal_error(mock_storage, mock_context):
    """Test get story with internal error."""
    # Arrange
    mock_storage.get_story.side_effect = Exception("Database error")
    request = planning_pb2.GetStoryRequest(story_id="STORY-001")

    # Act
    response = await get_story(request, mock_context, mock_storage)

    # Assert
    assert response.story_id == ""  # Empty story on error
    mock_context.set_code.assert_called_once()

