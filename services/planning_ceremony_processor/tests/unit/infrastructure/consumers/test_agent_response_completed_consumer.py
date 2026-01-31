"""Unit tests for AgentResponseCompletedConsumer."""

import asyncio
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
    """Consumer start creates subscription and polling task; stop cancels and re-raises CancelledError."""
    consumer = AgentResponseCompletedConsumer(
        nats_client=mock_nc, jetstream=mock_js, max_deliveries=3
    )
    await consumer.start()
    mock_js.pull_subscribe.assert_awaited_once()
    assert consumer._polling_task is not None

    with pytest.raises(asyncio.CancelledError):
        await consumer.stop()


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


@pytest.mark.asyncio
async def test_agent_response_completed_consumer_calls_advance_use_case_when_provided(
    mock_nc: MagicMock, mock_js: MagicMock
) -> None:
    """When advance_use_case is provided, handler calls advance with correlation_id/task_id/payload then acks."""
    advance_use_case = MagicMock()
    advance_use_case.advance = AsyncMock()

    envelope = create_event_envelope(
        event_type="agent.response.completed",
        payload={"task_id": "t1", "trigger": "deliberation_done"},
        producer="test",
        entity_id="e1",
        correlation_id="corr-1",
    )
    data = EventEnvelopeMapper.to_dict(envelope)

    consumer = AgentResponseCompletedConsumer(
        nats_client=mock_nc,
        jetstream=mock_js,
        max_deliveries=3,
        advance_use_case=advance_use_case,
    )
    msg = MagicMock()
    msg.data = json.dumps(data).encode("utf-8")
    msg.ack = AsyncMock()
    msg.metadata = MagicMock(num_delivered=1)

    await consumer._handle_message(msg)

    advance_use_case.advance.assert_awaited_once_with(
        correlation_id="corr-1",
        task_id="t1",
        payload={"task_id": "t1", "trigger": "deliberation_done"},
    )
    msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_agent_response_completed_consumer_acks_even_when_advance_raises_value_error(
    mock_nc: MagicMock, mock_js: MagicMock
) -> None:
    """When advance_use_case raises ValueError, handler logs and still acks."""
    advance_use_case = MagicMock()
    advance_use_case.advance = AsyncMock(
        side_effect=ValueError("transition guards not satisfied")
    )

    envelope = create_event_envelope(
        event_type="agent.response.completed",
        payload={"task_id": "t1", "trigger": "deliberation_done"},
        producer="test",
        entity_id="e1",
        correlation_id="corr-1",
    )
    data = EventEnvelopeMapper.to_dict(envelope)

    consumer = AgentResponseCompletedConsumer(
        nats_client=mock_nc,
        jetstream=mock_js,
        max_deliveries=3,
        advance_use_case=advance_use_case,
    )
    msg = MagicMock()
    msg.data = json.dumps(data).encode("utf-8")
    msg.ack = AsyncMock()
    msg.metadata = MagicMock(num_delivered=1)

    await consumer._handle_message(msg)

    msg.ack.assert_awaited_once()
