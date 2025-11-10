"""Unit tests for StoryTransitionedConsumer."""

import json
from unittest.mock import AsyncMock, Mock

import pytest

from core.context.domain.entity_ids.story_id import StoryId
from core.context.domain.phase_transition import PhaseTransition
from services.context.consumers.planning.story_transitioned_consumer import StoryTransitionedConsumer


@pytest.mark.asyncio
async def test_story_transitioned_consumer_calls_use_case():
    """Test that consumer calls HandleStoryPhaseTransitionUseCase."""
    # Arrange
    mock_js = AsyncMock()
    mock_use_case = AsyncMock()
    
    consumer = StoryTransitionedConsumer(
        js=mock_js,
        use_case=mock_use_case,
    )

    msg = Mock()
    event_data = {
        "story_id": "US-123",
        "from_phase": "draft",
        "to_phase": "po_review",
        "transitioned_by": "po@example.com",
        "timestamp_ms": 1699545600000,
    }
    msg.data = json.dumps(event_data).encode()
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()

    # Act
    await consumer._handle_message(msg)

    # Assert
    mock_use_case.execute.assert_awaited_once()
    call_args = mock_use_case.execute.call_args
    transition = call_args[0][0]  # First positional argument

    assert isinstance(transition, PhaseTransition)
    assert transition.story_id.value == "US-123"
    assert transition.from_phase == "draft"
    assert transition.to_phase == "po_review"
    assert transition.transitioned_by == "po@example.com"
    assert transition.timestamp_ms == 1699545600000

    msg.ack.assert_awaited_once()
    msg.nak.assert_not_awaited()


@pytest.mark.asyncio
async def test_story_transitioned_consumer_handles_use_case_error():
    """Test that consumer NAKs message on use case error."""
    # Arrange
    mock_js = AsyncMock()
    mock_use_case = AsyncMock()
    mock_use_case.execute.side_effect = Exception("Cache error")

    consumer = StoryTransitionedConsumer(
        js=mock_js,
        use_case=mock_use_case,
    )

    msg = Mock()
    msg.data = json.dumps({
        "story_id": "US-789",
        "from_phase": "draft",
        "to_phase": "invalid_phase",
        "transitioned_by": "system",
        "timestamp_ms": 1699545600000,
    }).encode()
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()

    # Act
    await consumer._handle_message(msg)

    # Assert
    msg.ack.assert_not_awaited()
    msg.nak.assert_awaited_once()


@pytest.mark.asyncio
async def test_story_transitioned_consumer_handles_invalid_json():
    """Test that consumer NAKs message on invalid JSON."""
    # Arrange
    mock_js = AsyncMock()
    mock_use_case = AsyncMock()
    
    consumer = StoryTransitionedConsumer(
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
async def test_story_transitioned_consumer_handles_missing_required_fields():
    """Test that consumer NAKs message when required fields are missing."""
    # Arrange
    mock_js = AsyncMock()
    mock_use_case = AsyncMock()
    
    consumer = StoryTransitionedConsumer(
        js=mock_js,
        use_case=mock_use_case,
    )

    msg = Mock()
    # Missing from_phase (required field)
    msg.data = json.dumps({
        "story_id": "US-123",
        "to_phase": "po_review",
    }).encode()
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()

    # Act
    await consumer._handle_message(msg)

    # Assert
    msg.ack.assert_not_awaited()
    msg.nak.assert_awaited_once()
    mock_use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_story_transitioned_consumer_handles_multiple_transitions():
    """Test consumer processes multiple transitions correctly."""
    # Arrange
    mock_js = AsyncMock()
    mock_use_case = AsyncMock()
    
    consumer = StoryTransitionedConsumer(
        js=mock_js,
        use_case=mock_use_case,
    )

    transitions = [
        ("draft", "po_review"),
        ("po_review", "coach_refinement"),
        ("coach_refinement", "ready_for_dev"),
    ]

    for from_phase, to_phase in transitions:
        msg = Mock()
        event_data = {
            "story_id": "US-FLOW",
            "from_phase": from_phase,
            "to_phase": to_phase,
            "transitioned_by": "system",
            "timestamp_ms": 1699545600000,
        }
        msg.data = json.dumps(event_data).encode()
        msg.ack = AsyncMock()
        msg.nak = AsyncMock()

        # Act
        await consumer._handle_message(msg)

        # Assert
        msg.ack.assert_awaited_once()

    # Should have been called 3 times
    assert mock_use_case.execute.await_count == 3


def test_story_transitioned_consumer_initialization():
    """Test StoryTransitionedConsumer initialization."""
    # Arrange
    mock_js = Mock()
    mock_use_case = Mock()

    # Act
    consumer = StoryTransitionedConsumer(
        js=mock_js,
        use_case=mock_use_case,
    )

    # Assert
    assert consumer.js == mock_js
    assert consumer._use_case == mock_use_case
    assert consumer.graph is None  # Inherited but not used
    assert consumer.cache is None  # Inherited but not used

