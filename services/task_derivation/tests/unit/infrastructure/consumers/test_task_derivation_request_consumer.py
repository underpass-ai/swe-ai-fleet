"""Tests for TaskDerivationRequestConsumer."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from task_derivation.infrastructure.consumers.task_derivation_request_consumer import (
    TaskDerivationRequestConsumer,
)
from task_derivation.infrastructure.nats_subjects import (
    TaskDerivationRequestSubjects,
)


class DummySubscription:
    def __init__(self, message):
        self._message = message

    async def fetch(self, batch: int):
        await asyncio.sleep(0)
        return [self._message]


class DummyMsg:
    def __init__(self, payload: dict[str, str], deliveries: int = 1):
        self.data = json.dumps(payload).encode("utf-8")
        self.metadata = SimpleNamespace(num_delivered=deliveries)
        self.ack = AsyncMock()
        self.nak = AsyncMock()


@pytest.mark.asyncio
async def test_request_consumer_acknowledges_on_success(monkeypatch) -> None:
    usecase = AsyncMock()
    msg = DummyMsg(
        {
            "plan_id": "plan-1",
            "story_id": "story-1",
            "roles": ["DEVELOPER"],
            "requested_by": "user",
        }
    )

    consumer = TaskDerivationRequestConsumer(
        nats_client=None,
        jetstream=None,
        derive_tasks_usecase=usecase,
    )

    consumer._subscription = DummySubscription(msg)

    async def run_once():
        await consumer._handle_message(msg)

    await run_once()

    msg.ack.assert_awaited_once()
    usecase.execute.assert_awaited()


@pytest.mark.asyncio
async def test_request_consumer_ack_on_validation_error() -> None:
    usecase = AsyncMock()
    msg = DummyMsg({"story_id": "story-1", "requested_by": "user"})

    consumer = TaskDerivationRequestConsumer(
        nats_client=None,
        jetstream=None,
        derive_tasks_usecase=usecase,
    )

    await consumer._handle_message(msg)

    msg.ack.assert_awaited_once()
    usecase.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_request_consumer_naks_until_max_deliveries() -> None:
    usecase = AsyncMock()
    usecase.execute.side_effect = RuntimeError("boom")
    msg = DummyMsg(
        {
            "plan_id": "plan-1",
            "story_id": "story-1",
            "roles": ["DEVELOPER"],
            "requested_by": "user",
        },
        deliveries=1,
    )

    consumer = TaskDerivationRequestConsumer(
        nats_client=None,
        jetstream=None,
        derive_tasks_usecase=usecase,
        max_deliveries=2,
    )

    await consumer._handle_message(msg)

    msg.nak.assert_awaited_once()

    msg.metadata.num_delivered = 2
    await consumer._handle_message(msg)
    msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_stop_cancels_polling_task_and_raises_cancelled_error() -> None:
    """Test that stop() cancels the polling task and re-raises CancelledError."""
    consumer = TaskDerivationRequestConsumer(
        nats_client=None,
        jetstream=None,
        derive_tasks_usecase=AsyncMock(),
    )

    # Arrange: Create a fake polling task that will be cancelled
    async def fake_polling():
        await asyncio.sleep(100)

    consumer._polling_task = asyncio.create_task(fake_polling())

    # Give the task a moment to start
    await asyncio.sleep(0.01)

    # Act & Assert: stop() should re-raise CancelledError after cleanup
    with pytest.raises(asyncio.CancelledError):
        await consumer.stop()

    # Assert: Task should be cancelled
    assert consumer._polling_task.cancelled()


@pytest.mark.asyncio
async def test_stop_handles_no_polling_task() -> None:
    """Test that stop() handles case where no polling task exists."""
    consumer = TaskDerivationRequestConsumer(
        nats_client=None,
        jetstream=None,
        derive_tasks_usecase=AsyncMock(),
    )
    consumer._polling_task = None

    # Act: Should not raise
    await consumer.stop()

    # Assert: Consumer stopped successfully
    assert consumer._polling_task is None


@pytest.mark.asyncio
async def test_stop_logs_cancellation_before_raising(caplog) -> None:
    """Test that stop() logs cancellation message before re-raising CancelledError."""
    import logging

    caplog.set_level(logging.INFO)

    consumer = TaskDerivationRequestConsumer(
        nats_client=None,
        jetstream=None,
        derive_tasks_usecase=AsyncMock(),
    )

    # Arrange: Create a fake polling task
    async def fake_polling():
        await asyncio.sleep(100)

    consumer._polling_task = asyncio.create_task(fake_polling())

    # Act & Assert: Should raise CancelledError
    with pytest.raises(asyncio.CancelledError):
        await consumer.stop()

    # Assert: Logging message should be present
    assert "TaskDerivationRequestConsumer polling task cancelled" in caplog.text


@pytest.mark.asyncio
async def test_poll_raises_cancelled_error_when_cancelled() -> None:
    """Test that _poll() properly re-raises CancelledError when cancelled."""
    consumer = TaskDerivationRequestConsumer(
        nats_client=None,
        jetstream=None,
        derive_tasks_usecase=AsyncMock(),
    )

    # Arrange: Mock subscription that raises CancelledError
    mock_subscription = AsyncMock()
    mock_subscription.fetch = AsyncMock(side_effect=asyncio.CancelledError())
    consumer._subscription = mock_subscription

    # Act & Assert: Should raise CancelledError
    with pytest.raises(asyncio.CancelledError):
        await consumer._poll()

    # Assert: Fetch was called
    mock_subscription.fetch.assert_awaited()


@pytest.mark.asyncio
async def test_start_subscribes_and_starts_polling() -> None:
    """Test that start() subscribes to NATS and starts polling task."""
    mock_jetstream = AsyncMock()
    mock_subscription = AsyncMock()
    mock_jetstream.pull_subscribe = AsyncMock(return_value=mock_subscription)

    consumer = TaskDerivationRequestConsumer(
        nats_client=None,
        jetstream=mock_jetstream,
        derive_tasks_usecase=AsyncMock(),
    )

    await consumer.start()

    mock_jetstream.pull_subscribe.assert_awaited_once_with(
        subject=TaskDerivationRequestSubjects.SUBJECT,
        durable=TaskDerivationRequestSubjects.DURABLE,
        stream=TaskDerivationRequestSubjects.STREAM,
    )
    assert consumer._subscription == mock_subscription
    assert consumer._polling_task is not None

    # Cleanup: Cancel task to avoid hanging
    consumer._polling_task.cancel()
    # Don't await cancelled task - just cancel it to prevent hanging


# Note: We don't test _poll() directly because it contains an infinite loop (while True)
# Instead, we test the behavior through _handle_message() and integration tests


# Note: We don't test _poll() directly because it contains an infinite loop (while True)
# Instead, we test the behavior through _handle_message() and integration tests


# Note: We don't test _poll() directly because it contains an infinite loop (while True)
# Instead, we test message processing through _handle_message() tests

