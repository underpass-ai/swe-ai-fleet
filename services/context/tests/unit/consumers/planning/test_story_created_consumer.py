"""Unit tests for StoryCreatedConsumer."""

import json
from unittest.mock import AsyncMock, Mock

import pytest
from core.context.domain.story import Story
from core.shared.events.event_envelope import EventEnvelope
from core.shared.events.infrastructure import EventEnvelopeMapper
from services.context.consumers.planning.story_created_consumer import StoryCreatedConsumer


def _make_enveloped_msg(payload: dict[str, object]) -> Mock:
    msg = Mock()
    envelope = EventEnvelope(
        event_type="planning.story.created",
        payload=payload,
        idempotency_key="idemp-test-story-created",
        correlation_id="corr-test-story-created",
        timestamp="2025-12-30T10:00:00+00:00",
        producer="context-tests",
    )
    msg.data = json.dumps(EventEnvelopeMapper.to_dict(envelope)).encode()
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()
    return msg


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

    event_data = {
        "story_id": "US-123",
        "epic_id": "EPIC-456",
        "name": "User Registration",
    }
    msg = _make_enveloped_msg(event_data)

    # Act
    await consumer._handle_message(msg)

    # Assert
    mock_use_case.execute.assert_awaited_once()
    call_args = mock_use_case.execute.call_args
    story = call_args[0][0]  # First positional argument

    assert isinstance(story, Story)
    assert story.story_id.value == "US-123"
    assert story.epic_id.value == "EPIC-456"
    assert story.name == "User Registration"

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

    msg = _make_enveloped_msg(
        {
            "story_id": "US-789",
            "epic_id": "EPIC-123",
            "name": "Failed Story",
        }
    )

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
async def test_story_created_consumer_uses_envelope_payload_inner_dict():
    """Verify consumer uses envelope.payload (inner event data), not top-level keys.

    Message structure: { event_type, payload: { story_id, epic_id, name/title }, ... }.
    The mapper must receive the inner payload dict; epic_id and story_id must not
    be read from the top-level envelope.
    """
    mock_js = AsyncMock()
    mock_use_case = AsyncMock()
    consumer = StoryCreatedConsumer(js=mock_js, use_case=mock_use_case)

    # Inner payload (as published by Planning): story_id, epic_id, title
    inner_payload = {
        "story_id": "s-inner-123",
        "epic_id": "E-inner-456",
        "title": "As a user I want to sign up",
    }
    msg = _make_enveloped_msg(inner_payload)

    await consumer._handle_message(msg)

    mock_use_case.execute.assert_awaited_once()
    story = mock_use_case.execute.call_args[0][0]
    assert story.story_id.value == "s-inner-123"
    assert story.epic_id.value == "E-inner-456"
    assert story.name == "As a user I want to sign up"  # title → name
    msg.ack.assert_awaited_once()


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

    # Missing story_id (required field)
    msg = _make_enveloped_msg({"epic_id": "EPIC-123", "name": "Incomplete Story"})

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

