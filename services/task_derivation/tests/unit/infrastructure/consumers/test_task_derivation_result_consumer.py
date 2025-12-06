"""Tests for TaskDerivationResultConsumer."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from task_derivation.application.usecases.process_task_derivation_result_usecase import (
    ProcessTaskDerivationResultUseCase,
)
from task_derivation.infrastructure.consumers.task_derivation_result_consumer import (
    TaskDerivationResultConsumer,
)

# Note: Consumer now uses handler internally, so we don't need to import mapper


class DummyMsg:
    def __init__(self, payload: dict[str, object], deliveries: int = 1):
        self.data = json.dumps(payload).encode("utf-8")
        self.metadata = SimpleNamespace(num_delivered=deliveries)
        self.ack = AsyncMock()
        self.nak = AsyncMock()


@pytest.mark.asyncio
async def test_result_consumer_invokes_usecase_and_acknowledges(monkeypatch) -> None:
    """Test consumer invokes use case via handler and acknowledges message."""
    usecase = AsyncMock(spec=ProcessTaskDerivationResultUseCase)
    messaging_port = AsyncMock()
    payload = {
        "plan_id": "plan-1",
        "story_id": "story-1",
        "role": "DEVELOPER",
        "result": {
            "proposal": "TITLE: Task\nDESCRIPTION: Do work\nESTIMATED_HOURS: 8\nPRIORITY: 1\nKEYWORDS: work",
        },
    }
    msg = DummyMsg(payload)

    consumer = TaskDerivationResultConsumer(
        nats_client=None,
        jetstream=None,
        process_usecase=usecase,
        messaging_port=messaging_port,
    )

    await consumer._handle_message(msg)

    msg.ack.assert_awaited_once()
    usecase.execute.assert_awaited()


@pytest.mark.asyncio
async def test_result_consumer_publishes_failure_on_validation_error() -> None:
    """Test consumer publishes failure event on validation error (empty proposal)."""
    usecase = AsyncMock(spec=ProcessTaskDerivationResultUseCase)
    messaging_port = AsyncMock()

    payload = {
        "plan_id": "plan-1",
        "story_id": "story-1",
        "role": "DEVELOPER",
        "result": {"proposal": ""},  # Empty proposal triggers ValueError
    }
    msg = DummyMsg(payload)

    consumer = TaskDerivationResultConsumer(
        nats_client=None,
        jetstream=None,
        process_usecase=usecase,
        messaging_port=messaging_port,
    )

    await consumer._handle_message(msg)

    msg.ack.assert_awaited_once()
    messaging_port.publish_task_derivation_failed.assert_awaited()
    usecase.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_result_consumer_retries_then_acknowledges() -> None:
    """Test consumer retries on transient error, then acknowledges after max deliveries."""
    usecase = AsyncMock(spec=ProcessTaskDerivationResultUseCase)
    usecase.execute.side_effect = RuntimeError("transient")
    messaging_port = AsyncMock()

    payload = {
        "plan_id": "plan-1",
        "story_id": "story-1",
        "role": "DEVELOPER",
        "result": {
            "proposal": "TITLE: Task\nDESCRIPTION: Body\nESTIMATED_HOURS: 8\nPRIORITY: 1\nKEYWORDS: test",
        },
    }
    msg = DummyMsg(payload, deliveries=1)

    consumer = TaskDerivationResultConsumer(
        nats_client=None,
        jetstream=None,
        process_usecase=usecase,
        messaging_port=messaging_port,
        max_deliveries=2,
    )

    await consumer._handle_message(msg)
    msg.nak.assert_awaited_once()

    msg.metadata.num_delivered = 2
    await consumer._handle_message(msg)
    msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_result_consumer_start_subscribes_and_starts_polling() -> None:
    """Test that start() subscribes to NATS and starts polling task."""
    mock_jetstream = AsyncMock()
    mock_subscription = AsyncMock()
    mock_jetstream.pull_subscribe = AsyncMock(return_value=mock_subscription)
    consumer = TaskDerivationResultConsumer(
        nats_client=None,
        jetstream=mock_jetstream,
        process_usecase=AsyncMock(),
        messaging_port=AsyncMock(),
    )

    with patch(
        "task_derivation.infrastructure.consumers.task_derivation_result_consumer.asyncio.create_task",
        return_value=AsyncMock(),
    ) as mock_create_task:
        await consumer.start()

    mock_jetstream.pull_subscribe.assert_awaited_once_with(
        subject="agent.response.completed",
        durable="task-derivation-result-consumer",
        stream="AGENT_RESPONSES",
    )
    assert consumer._subscription == mock_subscription
    mock_create_task.assert_called_once()


@pytest.mark.asyncio
async def test_result_consumer_stop_cancels_polling_task() -> None:
    """Test that stop() cancels the polling task."""
    consumer = TaskDerivationResultConsumer(
        nats_client=None,
        jetstream=None,
        process_usecase=AsyncMock(),
        messaging_port=AsyncMock(),
    )

    async def sleepy() -> None:
        await asyncio.sleep(10)

    consumer._polling_task = asyncio.create_task(sleepy())
    await asyncio.sleep(0)  # ensure task starts

    with pytest.raises(asyncio.CancelledError):
        await consumer.stop()
    assert consumer._polling_task.cancelled()


@pytest.mark.asyncio
async def test_result_consumer_stop_handles_no_polling_task() -> None:
    """Test that stop() handles case where no polling task exists."""
    consumer = TaskDerivationResultConsumer(
        nats_client=None,
        jetstream=None,
        process_usecase=AsyncMock(),
        messaging_port=AsyncMock(),
    )
    consumer._polling_task = None

    # Act: Should not raise
    await consumer.stop()

    # Assert: Consumer stopped successfully
    assert consumer._polling_task is None


# Note: We don't test _poll() directly because it contains an infinite loop (while True)
# Instead, we test the behavior through _handle_message() and integration tests


# Note: We don't test _poll() directly because it contains an infinite loop (while True)
# Instead, we test the behavior through _handle_message() and integration tests


# Note: We don't test _poll() directly because it contains an infinite loop (while True)
# Instead, we test the behavior through _handle_message() and integration tests


@pytest.mark.asyncio
async def test_result_consumer_extract_identifiers_success() -> None:
    """Test _extract_identifiers extracts plan_id and story_id correctly."""
    consumer = TaskDerivationResultConsumer(
        nats_client=None,
        jetstream=None,
        process_usecase=AsyncMock(),
        messaging_port=AsyncMock(),
    )

    payload = {"plan_id": "plan-123", "story_id": "story-456"}

    plan_id, story_id = consumer._extract_identifiers(payload)

    assert plan_id.value == "plan-123"
    assert story_id.value == "story-456"


@pytest.mark.asyncio
async def test_result_consumer_extract_identifiers_missing_plan_id() -> None:
    """Test _extract_identifiers raises ValueError for missing plan_id."""
    consumer = TaskDerivationResultConsumer(
        nats_client=None,
        jetstream=None,
        process_usecase=AsyncMock(),
        messaging_port=AsyncMock(),
    )

    payload = {"story_id": "story-456"}

    with pytest.raises(ValueError, match="plan_id missing"):
        consumer._extract_identifiers(payload)


@pytest.mark.asyncio
async def test_result_consumer_extract_identifiers_missing_story_id() -> None:
    """Test _extract_identifiers raises ValueError for missing story_id."""
    consumer = TaskDerivationResultConsumer(
        nats_client=None,
        jetstream=None,
        process_usecase=AsyncMock(),
        messaging_port=AsyncMock(),
    )

    payload = {"plan_id": "plan-123"}

    with pytest.raises(ValueError, match="story_id missing"):
        consumer._extract_identifiers(payload)


@pytest.mark.asyncio
async def test_result_consumer_publish_failure_from_consumer_success() -> None:
    """Test _publish_failure_from_consumer publishes failure event."""
    messaging_port = AsyncMock()
    consumer = TaskDerivationResultConsumer(
        nats_client=None,
        jetstream=None,
        process_usecase=AsyncMock(),
        messaging_port=messaging_port,
    )

    payload = {"plan_id": "plan-123", "story_id": "story-456"}

    await consumer._publish_failure_from_consumer(payload, "Test failure reason")

    messaging_port.publish_task_derivation_failed.assert_awaited_once()
    call_args = messaging_port.publish_task_derivation_failed.call_args[0][0]
    assert call_args.plan_id.value == "plan-123"
    assert call_args.story_id.value == "story-456"
    assert call_args.reason == "Test failure reason"


@pytest.mark.asyncio
async def test_result_consumer_publish_failure_from_consumer_missing_identifiers() -> None:
    """Test _publish_failure_from_consumer handles missing identifiers gracefully."""
    messaging_port = AsyncMock()
    consumer = TaskDerivationResultConsumer(
        nats_client=None,
        jetstream=None,
        process_usecase=AsyncMock(),
        messaging_port=messaging_port,
    )

    payload = {}  # Missing identifiers

    await consumer._publish_failure_from_consumer(payload, "Test failure reason")

    # Should not publish (logs error instead)
    messaging_port.publish_task_derivation_failed.assert_not_awaited()

