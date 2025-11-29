"""Tests for get_story handler."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from planning.application.usecases.get_story_usecase import GetStoryUseCase
from planning.domain import DORScore, Story, StoryId, StoryState, StoryStateEnum, Title, Brief, UserName
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.gen import planning_pb2
from planning.infrastructure.grpc.handlers.get_story_handler import get_story_handler


@pytest.fixture
def mock_use_case():
    """Create mock GetStoryUseCase."""
    return AsyncMock(spec=GetStoryUseCase)


@pytest.fixture
def mock_context():
    """Create mock gRPC context."""
    return Mock()


@pytest.fixture
def sample_story():
    """Create a sample story for testing."""
    now = datetime.now(UTC)
    return Story(
        story_id=StoryId("STORY-001"),
        epic_id=EpicId("EPIC-001"),
        title=Title("Test Story"),
        brief=Brief("Test brief"),
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(85),
        created_by=UserName("test_user"),
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_get_story_success(mock_use_case, mock_context, sample_story):
    """Test getting story successfully."""
    # Arrange
    mock_use_case.execute.return_value = sample_story
    request = planning_pb2.GetStoryRequest(story_id="STORY-001")

    # Act
    response = await get_story_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.story_id == "STORY-001"
    assert response.title == "Test Story"
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_story_not_found(mock_use_case, mock_context):
    """Test getting story that doesn't exist."""
    # Arrange
    mock_use_case.execute.return_value = None
    request = planning_pb2.GetStoryRequest(story_id="NONEXISTENT")

    # Act
    response = await get_story_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.story_id == ""  # Empty story
    mock_context.set_code.assert_called_once()


@pytest.mark.asyncio
async def test_get_story_internal_error(mock_use_case, mock_context):
    """Test get story with internal error."""
    # Arrange
    mock_use_case.execute.side_effect = Exception("Database error")
    request = planning_pb2.GetStoryRequest(story_id="STORY-001")

    # Act
    response = await get_story_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.story_id == ""  # Empty story on error
    mock_context.set_code.assert_called_once()

