"""Unit tests for StoryCreatedConsumer."""

import json
from unittest.mock import AsyncMock, Mock

import pytest

from core.context.domain.entity_ids.epic_id import EpicId
from core.context.domain.entity_ids.story_id import StoryId
from core.context.domain.story import Story
from services.context.consumers.planning.story_created_consumer import StoryCreatedConsumer


@pytest.mark.asyncio
async def test_story_created_consumer_calls_use_case():
    """Test that consumer calls SynchronizeStoryFromPlanningUseCase."""
    # Arrange
    mock_js = AsyncMock()
    mock_use_case = AsyncMock()
    
    consumer = StoryCreatedConsumer(
        js=mock_js,
        use_case=mock_use_case,
    )

    msg = Mock()
    event_data = {
        "story_id": "US-123",
        "epic_id": "EPIC-456",
        "title": "User Registration",
        "brief": "As a user, I want to register",
        "state": "draft",
        "dor_score": 0,
        "created_by": "po@example.com",
        "created_at_ms": 1699545600000,
    }
    msg.data = json.dumps(event_data).encode()
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()

    # Act
    await consumer._handle_message(msg)

    # Assert
    mock_use_case.execute.assert_awaited_once()
    call_args = mock_use_case.execute.call_args
    story = call_args[0][0]  # First positional argument

    assert isinstance(story, Story)
    assert story.story_id.value == "US-123"
    assert story.epic_id.value == "EPIC-456"
    assert story.title == "User Registration"
    assert story.brief == "As a user, I want to register"

    msg.ack.assert_awaited_once()
    msg.nak.assert_not_awaited()


@pytest.mark.asyncio
async def test_story_created_consumer_handles_use_case_error():
    """Test that consumer NAKs message on use case error."""
    # Arrange
    mock_js = AsyncMock()
    mock_use_case = AsyncMock()
    mock_use_case.execute.side_effect = Exception("Database error")

    consumer = StoryCreatedConsumer(
        js=mock_js,
        use_case=mock_use_case,
    )

    msg = Mock()
    msg.data = json.dumps({
        "story_id": "US-789",
        "epic_id": "EPIC-123",
        "title": "Failed Story",
        "brief": "Brief",
        "created_at_ms": 1699545600000,
    }).encode()
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()

    # Act
    await consumer._handle_message(msg)

    # Assert
    msg.ack.assert_not_awaited()
    msg.nak.assert_awaited_once()


@pytest.mark.asyncio
async def test_story_created_consumer_handles_invalid_json():
    """Test that consumer NAKs message on invalid JSON."""
    # Arrange
    mock_js = AsyncMock()
    mock_use_case = AsyncMock()
    
    consumer = StoryCreatedConsumer(
        js=mock_js,
        use_case=mock_use_case,
    )

    msg = Mock()
    msg.data = b"invalid json{"
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()

    # Act
    await consumer._handle_message(msg)

    # Assert
    msg.ack.assert_not_awaited()
    msg.nak.assert_awaited_once()
    mock_use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_story_created_consumer_handles_missing_required_fields():
    """Test that consumer NAKs message when required fields are missing."""
    # Arrange
    mock_js = AsyncMock()
    mock_use_case = AsyncMock()
    
    consumer = StoryCreatedConsumer(
        js=mock_js,
        use_case=mock_use_case,
    )

    msg = Mock()
    # Missing story_id (required field)
    msg.data = json.dumps({
        "epic_id": "EPIC-123",
        "title": "Incomplete Story",
    }).encode()
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()

    # Act
    await consumer._handle_message(msg)

    # Assert
    msg.ack.assert_not_awaited()
    msg.nak.assert_awaited_once()
    mock_use_case.execute.assert_not_awaited()


def test_story_created_consumer_initialization():
    """Test StoryCreatedConsumer initialization."""
    # Arrange
    mock_js = Mock()
    mock_use_case = Mock()

    # Act
    consumer = StoryCreatedConsumer(
        js=mock_js,
        use_case=mock_use_case,
    )

    # Assert
    assert consumer.js == mock_js
    assert consumer._use_case == mock_use_case
    assert consumer.graph is None  # Inherited but not used
    assert consumer.cache is None  # Inherited but not used

