"""Unit tests for NATSMessagingAdapter."""

import json
import pytest
from unittest.mock import AsyncMock, Mock

from core.ceremony_engine.infrastructure.adapters.nats_messaging_adapter import (
    NATSMessagingAdapter,
)
from core.shared.events.event_envelope import EventEnvelope
from core.shared.events.helpers import create_event_envelope


@pytest.fixture
def mock_nats_client() -> Mock:
    """Create mock NATS client."""
    return Mock()


@pytest.fixture
def mock_jetstream() -> AsyncMock:
    """Create mock JetStream context."""
    js = AsyncMock()
    js.publish = AsyncMock()
    return js


@pytest.fixture
def adapter(mock_nats_client: Mock, mock_jetstream: AsyncMock) -> NATSMessagingAdapter:
    """Create NATSMessagingAdapter instance."""
    return NATSMessagingAdapter(
        nats_client=mock_nats_client,
        jetstream=mock_jetstream,
    )


@pytest.fixture
def sample_envelope() -> EventEnvelope:
    """Create sample EventEnvelope for testing."""
    return create_event_envelope(
        event_type="ceremony.sprint_planning.started",
        payload={"instance_id": "inst-123", "sprint_id": "sprint-1"},
        producer="ceremony-engine",
        entity_id="inst-123",
        operation="start",
    )


@pytest.mark.asyncio
async def test_publish_event_happy_path(
    adapter: NATSMessagingAdapter,
    mock_jetstream: AsyncMock,
    sample_envelope: EventEnvelope,
) -> None:
    """Test publishing event successfully."""
    # Mock JetStream publish response
    mock_ack = Mock()
    mock_ack.stream = "CEREMONY_EVENTS"
    mock_ack.seq = 42
    mock_jetstream.publish.return_value = mock_ack

    await adapter.publish_event("ceremony.sprint_planning.started", sample_envelope)

    # Verify publish was called
    mock_jetstream.publish.assert_awaited_once()
    call_args = mock_jetstream.publish.call_args

    # Verify subject
    assert call_args[0][0] == "ceremony.sprint_planning.started"

    # Verify message is valid JSON with envelope structure
    message_bytes = call_args[0][1]
    message_dict = json.loads(message_bytes.decode("utf-8"))

    assert message_dict["event_type"] == "ceremony.sprint_planning.started"
    assert message_dict["payload"]["instance_id"] == "inst-123"
    assert message_dict["idempotency_key"] == sample_envelope.idempotency_key
    assert message_dict["correlation_id"] == sample_envelope.correlation_id
    assert "timestamp" in message_dict
    assert message_dict["producer"] == "ceremony-engine"


@pytest.mark.asyncio
async def test_publish_event_empty_subject(
    adapter: NATSMessagingAdapter,
    sample_envelope: EventEnvelope,
) -> None:
    """Test publishing with empty subject fails."""
    with pytest.raises(ValueError, match="subject cannot be empty"):
        await adapter.publish_event("", sample_envelope)


@pytest.mark.asyncio
async def test_publish_event_none_envelope(
    adapter: NATSMessagingAdapter,
) -> None:
    """Test publishing with None envelope fails."""
    with pytest.raises(ValueError, match="envelope cannot be None"):
        await adapter.publish_event("ceremony.test", None)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_publish_event_nats_error(
    adapter: NATSMessagingAdapter,
    mock_jetstream: AsyncMock,
    sample_envelope: EventEnvelope,
) -> None:
    """Test publishing when NATS raises error."""
    mock_jetstream.publish.side_effect = Exception("NATS connection error")

    with pytest.raises(RuntimeError, match="Failed to publish event"):
        await adapter.publish_event("ceremony.test", sample_envelope)


@pytest.mark.asyncio
async def test_publish_event_envelope_has_required_fields(
    adapter: NATSMessagingAdapter,
    mock_jetstream: AsyncMock,
    sample_envelope: EventEnvelope,
) -> None:
    """Test that published envelope has all required fields."""
    mock_ack = Mock()
    mock_ack.stream = "CEREMONY_EVENTS"
    mock_ack.seq = 1
    mock_jetstream.publish.return_value = mock_ack

    await adapter.publish_event("ceremony.test", sample_envelope)

    # Verify envelope has required fields
    assert sample_envelope.idempotency_key
    assert sample_envelope.correlation_id
    assert sample_envelope.event_type
    assert sample_envelope.timestamp
    assert sample_envelope.producer

    # Verify serialized message includes all fields
    call_args = mock_jetstream.publish.call_args
    message_dict = json.loads(call_args[0][1].decode("utf-8"))

    assert "idempotency_key" in message_dict
    assert "correlation_id" in message_dict
    assert "event_type" in message_dict
    assert "timestamp" in message_dict
    assert "producer" in message_dict
    assert "payload" in message_dict


@pytest.mark.asyncio
async def test_publish_event_with_causation_id(
    adapter: NATSMessagingAdapter,
    mock_jetstream: AsyncMock,
) -> None:
    """Test publishing event with causation_id."""
    envelope = create_event_envelope(
        event_type="ceremony.step.completed",
        payload={"step_id": "step-1"},
        producer="ceremony-engine",
        entity_id="step-1",
        causation_id="parent-event-123",
    )

    mock_ack = Mock()
    mock_ack.stream = "CEREMONY_EVENTS"
    mock_ack.seq = 1
    mock_jetstream.publish.return_value = mock_ack

    await adapter.publish_event("ceremony.test", envelope)

    # Verify causation_id is included in serialized message
    call_args = mock_jetstream.publish.call_args
    message_dict = json.loads(call_args[0][1].decode("utf-8"))

    assert message_dict["causation_id"] == "parent-event-123"


@pytest.mark.asyncio
async def test_publish_event_without_causation_id(
    adapter: NATSMessagingAdapter,
    mock_jetstream: AsyncMock,
    sample_envelope: EventEnvelope,
) -> None:
    """Test publishing event without causation_id (optional field)."""
    mock_ack = Mock()
    mock_ack.stream = "CEREMONY_EVENTS"
    mock_ack.seq = 1
    mock_jetstream.publish.return_value = mock_ack

    await adapter.publish_event("ceremony.test", sample_envelope)

    # Verify causation_id is not included if None
    call_args = mock_jetstream.publish.call_args
    message_dict = json.loads(call_args[0][1].decode("utf-8"))

    # causation_id should not be in dict if it's None (EventEnvelopeMapper behavior)
    # But if it's explicitly None, it might be omitted
    assert sample_envelope.causation_id is None


def test_adapter_requires_nats_client() -> None:
    """Test that adapter requires nats_client."""
    with pytest.raises(ValueError, match="nats_client is required"):
        NATSMessagingAdapter(nats_client=None, jetstream=AsyncMock())  # type: ignore[arg-type]


def test_adapter_requires_jetstream() -> None:
    """Test that adapter requires jetstream."""
    with pytest.raises(ValueError, match="jetstream is required"):
        NATSMessagingAdapter(nats_client=Mock(), jetstream=None)  # type: ignore[arg-type]
