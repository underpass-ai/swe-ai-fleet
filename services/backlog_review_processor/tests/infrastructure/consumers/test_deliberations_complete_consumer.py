"""Unit tests for DeliberationsCompleteConsumer."""

# Mock the missing gen module FIRST before ANY imports
import sys
from unittest.mock import MagicMock

mock_gen = MagicMock()
sys.modules['backlog_review_processor.gen'] = mock_gen
sys.modules['backlog_review_processor.gen.agent_response_payload'] = MagicMock()

# Now safe to import
import asyncio
import json
from unittest.mock import AsyncMock, Mock

import pytest

from backlog_review_processor.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from backlog_review_processor.domain.value_objects.identifiers.story_id import StoryId
from backlog_review_processor.infrastructure.consumers.deliberations_complete_consumer import (
    DeliberationsCompleteConsumer,
)
from core.shared.events import EventEnvelope


@pytest.fixture
def mock_nats_client():
    """Mock NATS client."""
    return Mock()


@pytest.fixture
def mock_jetstream():
    """Mock JetStream context."""
    mock_js = AsyncMock()
    mock_js.pull_subscribe = AsyncMock()
    return mock_js


@pytest.fixture
def mock_extract_tasks_usecase():
    """Mock ExtractTasksFromDeliberationsUseCase."""
    mock_uc = AsyncMock()
    mock_uc.execute = AsyncMock()
    return mock_uc


@pytest.fixture
def consumer(mock_nats_client, mock_jetstream, mock_extract_tasks_usecase):
    """Create DeliberationsCompleteConsumer instance."""
    return DeliberationsCompleteConsumer(
        nats_client=mock_nats_client,
        jetstream=mock_jetstream,
        extract_tasks_usecase=mock_extract_tasks_usecase,
    )


@pytest.mark.asyncio
async def test_handle_message_with_envelope(consumer, mock_extract_tasks_usecase):
    """Test handling message with EventEnvelope format."""
    # Arrange
    ceremony_id = "BRC-123"
    story_id = "ST-456"

    envelope = EventEnvelope(
        event_type="planning.backlog_review.deliberations.complete",
        payload={
            "ceremony_id": ceremony_id,
            "story_id": story_id,
            "agent_deliberations": [
                {
                    "agent_id": "agent-1",
                    "role": "ARCHITECT",
                    "proposal": "test",
                    "deliberated_at": "2025-12-28T10:00:00Z",
                }
            ],
        },
        idempotency_key="key-123",
        correlation_id="corr-456",
        timestamp="2025-12-28T10:00:00+00:00",
        producer="backlog-review-processor",
    )

    mock_msg = AsyncMock()
    mock_msg.data = json.dumps(envelope.to_dict()).encode("utf-8")
    mock_msg.ack = AsyncMock()

    # Act
    await consumer._handle_message(mock_msg)

    # Assert
    mock_extract_tasks_usecase.execute.assert_awaited_once()
    call_args = mock_extract_tasks_usecase.execute.call_args

    # Verify ceremony_id and story_id were passed correctly
    assert call_args.kwargs["ceremony_id"].value == ceremony_id
    assert call_args.kwargs["story_id"].value == story_id
    assert len(call_args.kwargs["agent_deliberations"]) == 1

    mock_msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_legacy_format(consumer, mock_extract_tasks_usecase):
    """Test handling message with legacy format (no envelope)."""
    # Arrange
    ceremony_id = "BRC-123"
    story_id = "ST-456"

    payload = {
        "ceremony_id": ceremony_id,
        "story_id": story_id,
        "agent_deliberations": [
            {
                "agent_id": "agent-1",
                "role": "QA",
                "proposal": "test",
                "deliberated_at": "2025-12-28T10:00:00Z",
            }
        ],
    }

    mock_msg = AsyncMock()
    mock_msg.data = json.dumps(payload).encode("utf-8")
    mock_msg.ack = AsyncMock()

    # Act
    await consumer._handle_message(mock_msg)

    # Assert
    mock_extract_tasks_usecase.execute.assert_awaited_once()
    call_args = mock_extract_tasks_usecase.execute.call_args

    assert call_args.kwargs["ceremony_id"].value == ceremony_id
    assert call_args.kwargs["story_id"].value == story_id

    mock_msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_missing_ceremony_id(consumer):
    """Test handling message with missing ceremony_id."""
    # Arrange
    payload = {
        "story_id": "ST-456",
        "agent_deliberations": [],
    }

    mock_msg = AsyncMock()
    mock_msg.data = json.dumps(payload).encode("utf-8")
    mock_msg.nak = AsyncMock()

    # Act
    await consumer._handle_message(mock_msg)

    # Assert
    mock_msg.nak.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_missing_story_id(consumer):
    """Test handling message with missing story_id."""
    # Arrange
    payload = {
        "ceremony_id": "BRC-123",
        "agent_deliberations": [],
    }

    mock_msg = AsyncMock()
    mock_msg.data = json.dumps(payload).encode("utf-8")
    mock_msg.nak = AsyncMock()

    # Act
    await consumer._handle_message(mock_msg)

    # Assert
    mock_msg.nak.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_invalid_json(consumer):
    """Test handling message with invalid JSON."""
    # Arrange
    mock_msg = AsyncMock()
    mock_msg.data = b"invalid json {{"
    mock_msg.ack = AsyncMock()

    # Act
    await consumer._handle_message(mock_msg)

    # Assert - ACK (don't retry validation errors)
    mock_msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_usecase_error(consumer, mock_extract_tasks_usecase):
    """Test handling message when usecase raises error."""
    # Arrange
    payload = {
        "ceremony_id": "BRC-123",
        "story_id": "ST-456",
        "agent_deliberations": [],
    }

    mock_msg = AsyncMock()
    mock_msg.data = json.dumps(payload).encode("utf-8")
    mock_msg.nak = AsyncMock()

    mock_extract_tasks_usecase.execute.side_effect = Exception("Usecase error")

    # Act
    await consumer._handle_message(mock_msg)

    # Assert
    mock_msg.nak.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_creates_subscription(mock_nats_client, mock_jetstream, mock_extract_tasks_usecase):
    """Test that start creates a durable subscription."""
    # Arrange - Mock the subscription to avoid infinite polling
    mock_subscription = AsyncMock()
    mock_jetstream.pull_subscribe.return_value = mock_subscription
    
    consumer = DeliberationsCompleteConsumer(
        nats_client=mock_nats_client,
        jetstream=mock_jetstream,
        extract_tasks_usecase=mock_extract_tasks_usecase,
    )
    
    # Act - Just call start, don't await polling
    await consumer.start()
    
    # Assert
    mock_jetstream.pull_subscribe.assert_awaited_once()
    call_args = mock_jetstream.pull_subscribe.call_args
    
    # Verify subscription parameters
    assert "deliberations.complete" in str(call_args.kwargs.get("subject", ""))
    assert call_args.kwargs.get("durable") is not None
    assert call_args.kwargs.get("stream") is not None
    
    # Cleanup - cancel the polling task
    if consumer._polling_task:
        consumer._polling_task.cancel()


@pytest.mark.asyncio
async def test_start_handles_exception(consumer, mock_jetstream):
    """Test that start handles exceptions gracefully."""
    # Arrange
    mock_jetstream.pull_subscribe.side_effect = Exception("Connection error")

    # Act & Assert
    with pytest.raises(Exception, match="Connection error"):
        await consumer.start()


@pytest.mark.asyncio
async def test_stop_cancels_polling_task(consumer):
    """Test that stop cancels the polling task."""
    # Arrange
    # Create a real asyncio task that we can cancel
    async def dummy_task():
        await asyncio.sleep(100)  # Long sleep
    
    task = asyncio.create_task(dummy_task())
    consumer._polling_task = task

    # Act & Assert - Should raise CancelledError
    with pytest.raises(asyncio.CancelledError):
        await consumer.stop()
    
    # Verify task was cancelled
    assert task.cancelled()


@pytest.mark.asyncio
async def test_stop_no_polling_task(consumer):
    """Test that stop handles missing polling task."""
    # Arrange
    consumer._polling_task = None

    # Act - should not raise
    await consumer.stop()
