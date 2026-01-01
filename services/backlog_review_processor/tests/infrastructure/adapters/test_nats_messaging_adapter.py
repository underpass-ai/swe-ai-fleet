"""Unit tests for NATSMessagingAdapter."""

import json
from unittest.mock import AsyncMock, Mock

import pytest

from backlog_review_processor.infrastructure.adapters.nats_messaging_adapter import (
    NATSMessagingAdapter,
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
async def test_publish_event_legacy(adapter, mock_jetstream):
    """Test legacy publish_event method."""
    # Arrange
    subject = "test.subject"
    payload = {"key": "value", "number": 42}

    # Act
    await adapter.publish_event(subject, payload)

    # Assert
    mock_jetstream.publish.assert_awaited_once()
    call_args = mock_jetstream.publish.call_args
    assert call_args[0][0] == subject
    
    # Verify payload was serialized correctly
    published_data = call_args[0][1]
    assert isinstance(published_data, bytes)
    decoded_payload = json.loads(published_data.decode("utf-8"))
    assert decoded_payload == payload


@pytest.mark.asyncio
async def test_publish_event_with_envelope(adapter, mock_jetstream):
    """Test publish_event_with_envelope method."""
    # Arrange
    subject = "test.subject.with.envelope"
    envelope = EventEnvelope(
        event_type="test.event",
        payload={"story_id": "ST-123", "data": "test"},
        idempotency_key="test-key-123",
        correlation_id="corr-456",
        timestamp="2025-12-28T10:00:00+00:00",
        producer="test-service",
    )

    # Act
    await adapter.publish_event_with_envelope(subject, envelope)

    # Assert
    mock_jetstream.publish.assert_awaited_once()
    call_args = mock_jetstream.publish.call_args
    assert call_args[0][0] == subject
    
    # Verify envelope was serialized correctly
    published_data = call_args[0][1]
    assert isinstance(published_data, bytes)
    decoded_envelope = json.loads(published_data.decode("utf-8"))
    
    # Verify envelope structure
    assert decoded_envelope["event_type"] == "test.event"
    assert decoded_envelope["idempotency_key"] == "test-key-123"
    assert decoded_envelope["correlation_id"] == "corr-456"
    assert decoded_envelope["producer"] == "test-service"
    assert decoded_envelope["payload"] == {"story_id": "ST-123", "data": "test"}


@pytest.mark.asyncio
async def test_publish_event_with_envelope_includes_causation(adapter, mock_jetstream):
    """Test publish_event_with_envelope with causation_id."""
    # Arrange
    subject = "test.subject"
    envelope = EventEnvelope(
        event_type="test.event",
        payload={"data": "test"},
        idempotency_key="key-123",
        correlation_id="corr-456",
        timestamp="2025-12-28T10:00:00+00:00",
        producer="test-service",
        causation_id="cause-789",
        metadata={"user": "test"},
    )

    # Act
    await adapter.publish_event_with_envelope(subject, envelope)

    # Assert
    mock_jetstream.publish.assert_awaited_once()
    published_data = mock_jetstream.publish.call_args[0][1]
    decoded_envelope = json.loads(published_data.decode("utf-8"))
    
    assert decoded_envelope["causation_id"] == "cause-789"
    assert decoded_envelope["metadata"] == {"user": "test"}


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


@pytest.mark.asyncio
async def test_publish_event_with_envelope_raises_on_nats_error(adapter, mock_jetstream):
    """Test that publish_event_with_envelope raises RuntimeError on NATS failure."""
    # Arrange
    subject = "test.subject"
    envelope = EventEnvelope(
        event_type="test.event",
        payload={"data": "test"},
        idempotency_key="key-123",
        correlation_id="corr-456",
        timestamp="2025-12-28T10:00:00+00:00",
        producer="test-service",
    )
    mock_jetstream.publish.side_effect = Exception("NATS connection error")

    # Act & Assert
    with pytest.raises(RuntimeError, match="Failed to publish event"):
        await adapter.publish_event_with_envelope(subject, envelope)
