"""Tests for create_story handler."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from planning.domain import (
    Brief,
    DORScore,
    Story,
    StoryId,
    StoryState,
    StoryStateEnum,
    Title,
    UserName,
)
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.gen import planning_pb2
from planning.infrastructure.grpc.handlers.create_story_handler import (
    create_story_handler,
)


@pytest.fixture
def mock_use_case():
    """Create mock CreateStoryUseCase."""
    return AsyncMock()


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
async def test_create_story_success(mock_use_case, mock_context, sample_story):
    """Test creating story successfully."""
    # Arrange
    mock_use_case.execute.return_value = sample_story
    request = planning_pb2.CreateStoryRequest(
        epic_id="EPIC-001",
        title="Test Story",
        brief="Test brief",
        created_by="test_user",
    )

    # Act
    response = await create_story_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    assert "Story created" in response.message
    assert response.story.story_id == "STORY-001"
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_story_validation_error(mock_use_case, mock_context):
    """Test create with validation error (epic not found)."""
    # Arrange
    mock_use_case.execute.side_effect = ValueError("Epic not found")
    request = planning_pb2.CreateStoryRequest(
        epic_id="INVALID",
        title="Test",
        brief="Valid brief description",  # brief is now required
        created_by="user",
    )

    # Act
    response = await create_story_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is False
    assert "Epic not found" in response.message
    mock_context.set_code.assert_called_once()


@pytest.mark.asyncio
async def test_create_story_empty_brief_validation_error(mock_use_case, mock_context):
    """Test create with empty brief validation error."""
    # Arrange
    request = planning_pb2.CreateStoryRequest(
        epic_id="EPIC-001",
        title="Test",
        brief="",  # Empty brief should fail validation
        created_by="user",
    )

    # Act
    response = await create_story_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is False
    assert "Brief cannot be empty" in response.message
    mock_context.set_code.assert_called_once()


@pytest.mark.asyncio
async def test_create_story_internal_error(mock_use_case, mock_context):
    """Test create with internal error."""
    # Arrange
    mock_use_case.execute.side_effect = Exception("Database error")
    request = planning_pb2.CreateStoryRequest(
        epic_id="EPIC-001",
        title="Test",
        brief="Test",
        created_by="user",
    )

    # Act
    response = await create_story_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is False
    assert "Internal error" in response.message
    mock_context.set_code.assert_called_once()

