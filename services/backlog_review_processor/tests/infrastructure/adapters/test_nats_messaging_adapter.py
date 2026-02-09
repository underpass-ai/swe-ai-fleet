"""Unit tests for NATSMessagingAdapter."""

import json
from unittest.mock import AsyncMock, Mock

import pytest

from backlog_review_processor.infrastructure.adapters.nats_messaging_adapter import (
    NATSMessagingAdapter,
)

@pytest.fixture
def mock_nats_client():
    """Mock NATS client."""
    return Mock()


@pytest.fixture
def mock_jetstream():
    """Mock JetStream context."""
    mock_js = AsyncMock()
    mock_ack = Mock()
    mock_ack.stream = "test-stream"
    mock_ack.seq = 123
    mock_js.publish = AsyncMock(return_value=mock_ack)
    return mock_js


@pytest.fixture
def adapter(mock_nats_client, mock_jetstream):
    """Create NATSMessagingAdapter instance."""
    return NATSMessagingAdapter(
        nats_client=mock_nats_client,
        jetstream=mock_jetstream,
    )


@pytest.mark.asyncio
async def test_publish_event_wraps_payload_in_envelope(adapter, mock_jetstream):
    """Test publish_event wraps payload in EventEnvelope."""
    # Arrange
    subject = "test.subject"
    payload = {"key": "value", "number": 42}

    # Act
    await adapter.publish_event(subject, payload)

    # Assert
    mock_jetstream.publish.assert_awaited_once()
    call_args = mock_jetstream.publish.call_args
    assert call_args[0][0] == subject

    # Verify envelope was serialized correctly
    published_data = call_args[0][1]
    assert isinstance(published_data, bytes)
    decoded_envelope = json.loads(published_data.decode("utf-8"))
    assert decoded_envelope["event_type"] == subject
    assert decoded_envelope["producer"] == "backlog-review-processor"
    assert decoded_envelope["payload"] == payload
    assert "idempotency_key" in decoded_envelope
    assert "correlation_id" in decoded_envelope


@pytest.mark.asyncio
async def test_publish_event_raises_on_nats_error(adapter, mock_jetstream):
    """Test that publish_event raises RuntimeError on NATS failure."""
    # Arrange
    subject = "test.subject"
    payload = {"key": "value"}
    mock_jetstream.publish.side_effect = Exception("NATS connection error")

    # Act & Assert
    with pytest.raises(RuntimeError, match="Failed to publish event"):
        await adapter.publish_event(subject, payload)
