"""Tests for transition_story handler."""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timezone

from planning.domain.entities.story import Story
from planning.domain.value_objects.dor_score import DORScore
from planning.domain.value_objects.epic_id import EpicId
from planning.domain.value_objects.story_id import StoryId
from planning.domain.value_objects.story_state import StoryState, StoryStateEnum
from planning.gen import planning_pb2
from planning.infrastructure.grpc.handlers.transition_story_handler import transition_story


@pytest.fixture
def mock_use_case():
    """Create mock TransitionStoryUseCase."""
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
        state=StoryState(StoryStateEnum.IN_PROGRESS),
        dor_score=DORScore(85.0),
        created_by="test_user",
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_transition_story_success(mock_use_case, mock_context, sample_story):
    """Test transitioning story successfully."""
    # Arrange
    mock_use_case.execute.return_value = sample_story
    request = planning_pb2.TransitionStoryRequest(
        story_id="STORY-001",
        to_state=StoryStateEnum.IN_PROGRESS.value,
        transitioned_by="test_user",
    )

    # Act
    response = await transition_story(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    assert "transitioned to" in response.message
    assert response.story.story_id == "STORY-001"
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_transition_story_validation_error(mock_use_case, mock_context):
    """Test transition with invalid state."""
    # Arrange
    mock_use_case.execute.side_effect = ValueError("Invalid transition")
    request = planning_pb2.TransitionStoryRequest(
        story_id="STORY-001",
        to_state="INVALID_STATE",
        transitioned_by="test_user",
    )

    # Act
    response = await transition_story(request, mock_context, mock_use_case)

    # Assert
    assert response.success is False
    assert "Invalid" in response.message
    mock_context.set_code.assert_called_once()


@pytest.mark.asyncio
async def test_transition_story_internal_error(mock_use_case, mock_context):
    """Test transition with internal error."""
    # Arrange
    mock_use_case.execute.side_effect = Exception("Database error")
    request = planning_pb2.TransitionStoryRequest(
        story_id="STORY-001",
        to_state=StoryStateEnum.IN_PROGRESS.value,
        transitioned_by="test_user",
    )

    # Act
    response = await transition_story(request, mock_context, mock_use_case)

    # Assert
    assert response.success is False
    assert "Internal error" in response.message
    mock_context.set_code.assert_called_once()

