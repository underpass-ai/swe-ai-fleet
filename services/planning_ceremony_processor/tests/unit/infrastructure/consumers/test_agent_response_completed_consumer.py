"""Unit tests for AgentResponseCompletedConsumer."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.shared.events import create_event_envelope
from core.shared.events.infrastructure import EventEnvelopeMapper
from services.planning_ceremony_processor.infrastructure.consumers.agent_response_completed_consumer import (
    AgentResponseCompletedConsumer,
)


@pytest.fixture
def mock_nc() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_js() -> MagicMock:
    js = MagicMock()
    sub = MagicMock()
    sub.fetch = AsyncMock(return_value=[])
    js.pull_subscribe = AsyncMock(return_value=sub)
    return js


@pytest.mark.asyncio
async def test_agent_response_completed_consumer_start_stop(
    mock_nc: MagicMock, mock_js: MagicMock
) -> None:
    """Consumer start creates subscription and polling task; stop cancels it."""
    consumer = AgentResponseCompletedConsumer(
        nats_client=mock_nc, jetstream=mock_js, max_deliveries=3
    )
    await consumer.start()
    mock_js.pull_subscribe.assert_awaited_once()
    assert consumer._polling_task is not None

    await consumer.stop()
    assert consumer._polling_task is None or consumer._polling_task.cancelled()


@pytest.mark.asyncio
async def test_agent_response_completed_consumer_handle_message_acks_valid_envelope(
    mock_nc: MagicMock, mock_js: MagicMock
) -> None:
    """Handler parses EventEnvelope, logs, and acks."""
    envelope = create_event_envelope(
        event_type="agent.response.completed",
        payload={"task_id": "c1:s1", "status": "completed"},
        producer="test",
        entity_id="c1:s1",
        correlation_id="c1:s1",
    )
    data = EventEnvelopeMapper.to_dict(envelope)

    consumer = AgentResponseCompletedConsumer(
        nats_client=mock_nc, jetstream=mock_js, max_deliveries=3
    )
    msg = MagicMock()
    msg.data = json.dumps(data).encode("utf-8")
    msg.ack = AsyncMock()
    msg.metadata = MagicMock(num_delivered=1)

    await consumer._handle_message(msg)
    msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_agent_response_completed_consumer_handle_invalid_json_naks(
    mock_nc: MagicMock, mock_js: MagicMock
) -> None:
    """Handler naks on invalid JSON (until max_deliveries)."""
    consumer = AgentResponseCompletedConsumer(
        nats_client=mock_nc, jetstream=mock_js, max_deliveries=3
    )
    msg = MagicMock()
    msg.data = b"not json"
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()
    msg.metadata = MagicMock(num_delivered=1)

    await consumer._handle_message(msg)
    msg.nak.assert_awaited_once()
    msg.ack.assert_not_called()


@pytest.mark.asyncio
async def test_agent_response_completed_consumer_handle_invalid_json_acks_at_max_deliveries(
    mock_nc: MagicMock, mock_js: MagicMock
) -> None:
    """Handler acks invalid JSON when num_delivered >= max_deliveries."""
    consumer = AgentResponseCompletedConsumer(
        nats_client=mock_nc, jetstream=mock_js, max_deliveries=2
    )
    msg = MagicMock()
    msg.data = b"not json"
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()
    msg.metadata = MagicMock(num_delivered=2)

    await consumer._handle_message(msg)
    msg.ack.assert_awaited_once()
    msg.nak.assert_not_called()


@pytest.mark.asyncio
async def test_agent_response_completed_consumer_handle_invalid_envelope_acks(
    mock_nc: MagicMock, mock_js: MagicMock
) -> None:
    """Handler acks on invalid envelope (ValueError from parse_required_envelope)."""
    consumer = AgentResponseCompletedConsumer(
        nats_client=mock_nc, jetstream=mock_js, max_deliveries=3
    )
    msg = MagicMock()
    msg.data = json.dumps({"event_type": "x"}).encode("utf-8")  # missing required fields
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()
    msg.metadata = MagicMock(num_delivered=1)

    await consumer._handle_message(msg)
    msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_agent_response_completed_consumer_handle_message_no_metadata_num_delivered(
    mock_nc: MagicMock, mock_js: MagicMock
) -> None:
    """Handler uses delivery 1 when msg.metadata has no num_delivered (AttributeError path)."""
    envelope = create_event_envelope(
        event_type="agent.response.completed",
        payload={"task_id": "t1"},
        producer="test",
        entity_id="e1",
        correlation_id="c1",
    )
    data = EventEnvelopeMapper.to_dict(envelope)

    consumer = AgentResponseCompletedConsumer(
        nats_client=mock_nc, jetstream=mock_js, max_deliveries=3
    )
    msg = MagicMock()
    msg.data = json.dumps(data).encode("utf-8")
    msg.ack = AsyncMock()
    msg.metadata = MagicMock()
    del msg.metadata.num_delivered  # force getattr to use default

    await consumer._handle_message(msg)
    msg.ack.assert_awaited_once()
