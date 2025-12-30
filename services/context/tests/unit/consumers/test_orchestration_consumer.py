import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from core.shared.events.event_envelope import EventEnvelope
from core.shared.events.infrastructure import EventEnvelopeMapper
from services.context.consumers.orchestration_consumer import OrchestrationEventsConsumer


def _enveloped_bytes(event_type: str, payload: dict[str, object]) -> bytes:
    envelope = EventEnvelope(
        event_type=event_type,
        payload=payload,
        idempotency_key=f"idemp-test-{event_type}",
        correlation_id=f"corr-test-{event_type}",
        timestamp="2025-12-30T10:00:00+00:00",
        producer="context-tests",
    )
    return json.dumps(EventEnvelopeMapper.to_dict(envelope)).encode("utf-8")


async def _direct_to_thread(func, *args, **kwargs):
    return func(*args, **kwargs)


@pytest.mark.asyncio
async def test_handle_deliberation_completed_happy_path_acks_and_persists_decisions() -> None:
    consumer = OrchestrationEventsConsumer(
        nc=Mock(),
        js=AsyncMock(),
        graph_command=Mock(),
        nats_publisher=AsyncMock(),
    )
    consumer.project_decision.execute = Mock()

    msg = AsyncMock()
    msg.data = _enveloped_bytes(
        "orchestration.deliberation.completed",
        {
            "story_id": "story-1",
            "task_id": "task-1",
            "decisions": [{"id": "DEC-1", "type": "TECHNICAL", "rationale": "x"}],
            "timestamp": 123,
        },
    )
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()

    with patch(
        "services.context.consumers.orchestration_consumer.asyncio.to_thread",
        new=AsyncMock(side_effect=_direct_to_thread),
    ):
        await consumer._handle_deliberation_completed(msg)

    msg.ack.assert_awaited_once()
    msg.nak.assert_not_awaited()
    consumer.project_decision.execute.assert_called_once()
    consumer.publisher.publish_context_updated.assert_awaited_once_with(story_id="story-1", version=123)


@pytest.mark.asyncio
async def test_handle_deliberation_completed_drops_invalid_envelope() -> None:
    consumer = OrchestrationEventsConsumer(
        nc=Mock(),
        js=AsyncMock(),
        graph_command=Mock(),
        nats_publisher=None,
    )
    consumer.project_decision.execute = Mock()

    msg = AsyncMock()
    msg.data = json.dumps({"task_id": "x"}).encode("utf-8")  # missing envelope fields
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()

    await consumer._handle_deliberation_completed(msg)

    msg.ack.assert_awaited_once()
    consumer.project_decision.execute.assert_not_called()


@pytest.mark.asyncio
async def test_handle_task_dispatched_happy_path_acks_and_updates_status() -> None:
    consumer = OrchestrationEventsConsumer(
        nc=Mock(),
        js=AsyncMock(),
        graph_command=Mock(),
        nats_publisher=None,
    )
    consumer.update_subtask_status.execute = Mock()

    msg = AsyncMock()
    msg.data = _enveloped_bytes(
        "orchestration.task.dispatched",
        {
            "story_id": "story-1",
            "task_id": "task-1",
            "agent_id": "agent-1",
            "role": "DEV",
            "timestamp": 123,
        },
    )
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()

    with patch(
        "services.context.consumers.orchestration_consumer.asyncio.to_thread",
        new=AsyncMock(side_effect=_direct_to_thread),
    ):
        await consumer._handle_task_dispatched(msg)

    msg.ack.assert_awaited_once()
    msg.nak.assert_not_awaited()
    consumer.update_subtask_status.execute.assert_called_once()

