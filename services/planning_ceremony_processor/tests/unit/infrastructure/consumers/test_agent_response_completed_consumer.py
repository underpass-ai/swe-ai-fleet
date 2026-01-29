"""Unit tests for AgentResponseCompletedConsumer."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

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
async def test_agent_response_completed_consumer_start_raises_on_subscribe_failure(
    mock_nc: MagicMock, mock_js: MagicMock
) -> None:
    """start() re-raises when pull_subscribe fails."""
    mock_js.pull_subscribe = AsyncMock(side_effect=RuntimeError("nats unavailable"))
    consumer = AgentResponseCompletedConsumer(
        nats_client=mock_nc, jetstream=mock_js, max_deliveries=3
    )

    with pytest.raises(RuntimeError, match="nats unavailable"):
        await consumer.start()

    assert consumer._polling_task is None


@pytest.mark.asyncio
async def test_agent_response_completed_consumer_stop_when_no_polling_task(
    mock_nc: MagicMock, mock_js: MagicMock
) -> None:
    """stop() logs when _polling_task was never started."""
    consumer = AgentResponseCompletedConsumer(
        nats_client=mock_nc, jetstream=mock_js, max_deliveries=3
    )
    consumer._polling_task = None

    await consumer.stop()

    # No exception; stop is idempotent
    assert consumer._polling_task is None


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
async def test_agent_response_completed_consumer_handle_message_no_metadata_uses_deliveries_one(
    mock_nc: MagicMock, mock_js: MagicMock
) -> None:
    """Handler uses deliveries=1 when msg has no metadata (AttributeError)."""
    envelope = create_event_envelope(
        event_type="agent.response.completed",
        payload={"task_id": "t1"},
        producer="p",
        entity_id="e1",
        correlation_id="c1",
    )
    data = EventEnvelopeMapper.to_dict(envelope)

    consumer = AgentResponseCompletedConsumer(
        nats_client=mock_nc, jetstream=mock_js, max_deliveries=3
    )

    payload_bytes = json.dumps(data).encode("utf-8")

    class MsgNoMetadata:
        data = payload_bytes
        ack = AsyncMock()
        nak = AsyncMock()

        @property
        def metadata(self) -> None:
            raise AttributeError("no metadata")

    msg = MsgNoMetadata()

    await consumer._handle_message(msg)
    msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_agent_response_completed_consumer_handle_message_empty_correlation_and_payload(
    mock_nc: MagicMock, mock_js: MagicMock
) -> None:
    """Handler handles envelope with empty correlation_id and no task_id in payload."""
    envelope = create_event_envelope(
        event_type="agent.response.completed",
        payload={},
        producer="p",
        entity_id="e1",
        correlation_id="",
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
    msg.nak.assert_not_called()


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
    """Handler acks on invalid JSON when deliveries >= max_deliveries."""
    consumer = AgentResponseCompletedConsumer(
        nats_client=mock_nc, jetstream=mock_js, max_deliveries=3
    )
    msg = MagicMock()
    msg.data = b"not json"
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()
    msg.metadata = MagicMock(num_delivered=3)

    await consumer._handle_message(msg)

    msg.ack.assert_awaited_once()
    msg.nak.assert_not_called()


@pytest.mark.asyncio
async def test_agent_response_completed_consumer_handle_generic_exception_naks_below_max(
    mock_nc: MagicMock, mock_js: MagicMock
) -> None:
    """Handler naks on generic exception when deliveries < max_deliveries."""
    consumer = AgentResponseCompletedConsumer(
        nats_client=mock_nc, jetstream=mock_js, max_deliveries=3
    )
    msg = MagicMock()
    msg.data = json.dumps({"event_type": "x", "payload": None, "producer": "p", "entity_id": "e", "correlation_id": "c"}).encode("utf-8")
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()
    msg.metadata = MagicMock(num_delivered=2)

    with patch(
        "services.planning_ceremony_processor.infrastructure.consumers.agent_response_completed_consumer.parse_required_envelope",
        side_effect=RuntimeError("unexpected"),
    ):
        await consumer._handle_message(msg)

    msg.nak.assert_awaited_once()
    msg.ack.assert_not_called()


@pytest.mark.asyncio
async def test_agent_response_completed_consumer_handle_generic_exception_acks_at_max(
    mock_nc: MagicMock, mock_js: MagicMock
) -> None:
    """Handler acks on generic exception when deliveries >= max_deliveries."""
    consumer = AgentResponseCompletedConsumer(
        nats_client=mock_nc, jetstream=mock_js, max_deliveries=3
    )
    msg = MagicMock()
    msg.data = b'{"event_type":"x","payload":{},"producer":"p","entity_id":"e","correlation_id":"c"}'
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()
    msg.metadata = MagicMock(num_delivered=3)

    with patch(
        "services.planning_ceremony_processor.infrastructure.consumers.agent_response_completed_consumer.parse_required_envelope",
        side_effect=RuntimeError("unexpected"),
    ):
        await consumer._handle_message(msg)

    msg.ack.assert_awaited_once()
    msg.nak.assert_not_called()


@pytest.mark.asyncio
async def test_agent_response_completed_consumer_poll_messages_timeout_continues(
    mock_nc: MagicMock, mock_js: MagicMock
) -> None:
    """_poll_messages continues on TimeoutError then exits on CancelledError."""
    sub = MagicMock()
    sub.fetch = AsyncMock(side_effect=[TimeoutError(), asyncio.CancelledError()])
    mock_js.pull_subscribe = AsyncMock(return_value=sub)

    consumer = AgentResponseCompletedConsumer(
        nats_client=mock_nc, jetstream=mock_js, max_deliveries=3
    )
    consumer._subscription = sub

    with pytest.raises(asyncio.CancelledError):
        await consumer._poll_messages()

    assert sub.fetch.await_count == 2


@pytest.mark.asyncio
async def test_agent_response_completed_consumer_poll_messages_handles_message(
    mock_nc: MagicMock, mock_js: MagicMock
) -> None:
    """_poll_messages fetches and handles one message then exits on cancel."""
    envelope = create_event_envelope(
        event_type="agent.response.completed",
        payload={"task_id": "t1"},
        producer="p",
        entity_id="e1",
        correlation_id="c1",
    )
    data = EventEnvelopeMapper.to_dict(envelope)
    msg = MagicMock()
    msg.data = json.dumps(data).encode("utf-8")
    msg.ack = AsyncMock()
    msg.metadata = MagicMock(num_delivered=1)

    sub = MagicMock()
    sub.fetch = AsyncMock(side_effect=[[msg], asyncio.CancelledError()])
    mock_js.pull_subscribe = AsyncMock(return_value=sub)

    consumer = AgentResponseCompletedConsumer(
        nats_client=mock_nc, jetstream=mock_js, max_deliveries=3
    )
    consumer._subscription = sub

    with pytest.raises(asyncio.CancelledError):
        await consumer._poll_messages()

    msg.ack.assert_awaited_once()
    assert sub.fetch.await_count == 2


@pytest.mark.asyncio
async def test_agent_response_completed_consumer_poll_messages_exception_logs_and_sleeps(
    mock_nc: MagicMock, mock_js: MagicMock
) -> None:
    """_poll_messages on generic Exception logs and sleeps then exits on cancel."""
    sub = MagicMock()
    sub.fetch = AsyncMock(side_effect=[RuntimeError("fetch failed"), asyncio.CancelledError()])
    mock_js.pull_subscribe = AsyncMock(return_value=sub)

    consumer = AgentResponseCompletedConsumer(
        nats_client=mock_nc, jetstream=mock_js, max_deliveries=3
    )
    consumer._subscription = sub

    with patch(
        "services.planning_ceremony_processor.infrastructure.consumers.agent_response_completed_consumer.asyncio.sleep",
        new_callable=AsyncMock,
    ) as mock_sleep:
        with pytest.raises(asyncio.CancelledError):
            await consumer._poll_messages()

    mock_sleep.assert_awaited_once_with(5)
    assert sub.fetch.await_count == 2
