"""Unit tests for DualWriteReconcilerConsumer."""

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from core.shared.events import EventEnvelope
from core.shared.events.infrastructure import EventEnvelopeMapper

from planning.application.services.dual_write_reconciliation_service import (
    DualWriteReconciliationService,
)
from planning.infrastructure.consumers.dual_write_reconciler_consumer import (
    DualWriteReconcilerConsumer,
)


@pytest.fixture
def mock_nats_client() -> Mock:
    """Mock NATS client."""
    return Mock()


@pytest.fixture
def mock_jetstream() -> AsyncMock:
    """Mock JetStream context."""
    return AsyncMock()


@pytest.fixture
def mock_reconciliation_service() -> AsyncMock:
    """Mock reconciliation service."""
    return AsyncMock(spec=DualWriteReconciliationService)


@pytest.fixture
def consumer(
    mock_nats_client: Mock,
    mock_jetstream: AsyncMock,
    mock_reconciliation_service: AsyncMock,
) -> DualWriteReconcilerConsumer:
    """Create consumer with mocked dependencies."""
    return DualWriteReconcilerConsumer(
        nats_client=mock_nats_client,
        jetstream=mock_jetstream,
        reconciliation_service=mock_reconciliation_service,
    )


@pytest.mark.asyncio
async def test_start_creates_subscription(
    consumer: DualWriteReconcilerConsumer,
    mock_jetstream: AsyncMock,
) -> None:
    """Test that start() creates subscription."""
    mock_subscription = AsyncMock()
    mock_jetstream.pull_subscribe.return_value = mock_subscription

    await consumer.start()

    mock_jetstream.pull_subscribe.assert_awaited_once()
    assert consumer._subscription == mock_subscription
    assert consumer._polling_task is not None

    # Cleanup: Cancel task to avoid hanging
    consumer._polling_task.cancel()
    try:
        await asyncio.wait_for(consumer._polling_task, timeout=1.0)
    except (TimeoutError, asyncio.CancelledError):
        pass


@pytest.mark.asyncio
async def test_stop_cancels_polling_task(
    consumer: DualWriteReconcilerConsumer,
) -> None:
    """Test that stop() cancels polling task."""
    # Create a mock task
    mock_task = asyncio.create_task(asyncio.sleep(100))
    consumer._polling_task = mock_task

    # Stop should cancel the task
    try:
        await consumer.stop()
    except asyncio.CancelledError:
        pass  # Expected when task is cancelled

    assert mock_task.cancelled()


@pytest.mark.asyncio
async def test_handle_message_processes_successfully(
    consumer: DualWriteReconcilerConsumer,
    mock_reconciliation_service: AsyncMock,
) -> None:
    """Test that _handle_message() processes valid message successfully."""
    # Arrange: Create mock message with valid payload
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    envelope = EventEnvelope(
        event_type="planning.dualwrite.reconcile.requested",
        payload={
            "operation_id": "op-123",
            "operation_type": "save_story",
            "operation_data": {
                "story_id": "ST-1",
                "epic_id": "EP-1",
                "title": "Test Story",
                "created_by": "user1",
                "initial_state": "DRAFT",
            },
        },
        idempotency_key="idemp-test-op-123",
        correlation_id="corr-test-op-123",
        timestamp="2025-12-30T10:00:00+00:00",
        producer="planning-service",
    )
    mock_msg.data.decode.return_value = json.dumps(EventEnvelopeMapper.to_dict(envelope))

    # Act
    await consumer._handle_message(mock_msg)

    # Assert: Reconciliation service called with correct parameters
    mock_reconciliation_service.reconcile_operation.assert_awaited_once_with(
        operation_id="op-123",
        operation_type="save_story",
        operation_data={
            "story_id": "ST-1",
            "epic_id": "EP-1",
            "title": "Test Story",
            "created_by": "user1",
            "initial_state": "DRAFT",
        },
    )

    # Assert: Message ACKed
    mock_msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_handles_missing_operation_id(
    consumer: DualWriteReconcilerConsumer,
) -> None:
    """Test that _handle_message() handles missing operation_id."""
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    envelope = EventEnvelope(
        event_type="planning.dualwrite.reconcile.requested",
        payload={
            # Missing operation_id
            "operation_type": "save_story",
            "operation_data": {},
        },
        idempotency_key="idemp-test",
        correlation_id="corr-test",
        timestamp="2025-12-30T10:00:00+00:00",
        producer="planning-service",
    )
    mock_msg.data.decode.return_value = json.dumps(EventEnvelopeMapper.to_dict(envelope))

    # Act
    await consumer._handle_message(mock_msg)

    # Assert: Message NAKed (retry)
    mock_msg.nak.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_handles_missing_operation_type(
    consumer: DualWriteReconcilerConsumer,
) -> None:
    """Test that _handle_message() handles missing operation_type."""
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    envelope = EventEnvelope(
        event_type="planning.dualwrite.reconcile.requested",
        payload={
            "operation_id": "op-123",
            # Missing operation_type
            "operation_data": {},
        },
        idempotency_key="idemp-test",
        correlation_id="corr-test",
        timestamp="2025-12-30T10:00:00+00:00",
        producer="planning-service",
    )
    mock_msg.data.decode.return_value = json.dumps(EventEnvelopeMapper.to_dict(envelope))

    # Act
    await consumer._handle_message(mock_msg)

    # Assert: Message NAKed (retry)
    mock_msg.nak.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_handles_missing_operation_data(
    consumer: DualWriteReconcilerConsumer,
) -> None:
    """Test that _handle_message() handles missing operation_data."""
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    envelope = EventEnvelope(
        event_type="planning.dualwrite.reconcile.requested",
        payload={
            "operation_id": "op-123",
            "operation_type": "save_story",
            # Missing operation_data
        },
        idempotency_key="idemp-test",
        correlation_id="corr-test",
        timestamp="2025-12-30T10:00:00+00:00",
        producer="planning-service",
    )
    mock_msg.data.decode.return_value = json.dumps(EventEnvelopeMapper.to_dict(envelope))

    # Act
    await consumer._handle_message(mock_msg)

    # Assert: Message NAKed (retry)
    mock_msg.nak.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_handles_reconciliation_error(
    consumer: DualWriteReconcilerConsumer,
    mock_reconciliation_service: AsyncMock,
) -> None:
    """Test that _handle_message() handles reconciliation errors."""
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    envelope = EventEnvelope(
        event_type="planning.dualwrite.reconcile.requested",
        payload={
            "operation_id": "op-123",
            "operation_type": "save_story",
            "operation_data": {
                "story_id": "ST-1",
            },
        },
        idempotency_key="idemp-test",
        correlation_id="corr-test",
        timestamp="2025-12-30T10:00:00+00:00",
        producer="planning-service",
    )
    mock_msg.data.decode.return_value = json.dumps(EventEnvelopeMapper.to_dict(envelope))

    # Mock reconciliation service to raise error
    mock_reconciliation_service.reconcile_operation.side_effect = Exception(
        "Reconciliation failed"
    )

    # Act
    await consumer._handle_message(mock_msg)

    # Assert: Message NAKed (retry)
    mock_msg.nak.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_drops_invalid_envelope(
    consumer: DualWriteReconcilerConsumer,
) -> None:
    """Test that _handle_message() drops invalid envelope (ACK)."""
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    # Invalid JSON (not an EventEnvelope)
    mock_msg.data.decode.return_value = '{"invalid": "data"}'

    # Act
    await consumer._handle_message(mock_msg)

    # Assert: Message ACKed (dropped)
    mock_msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_poll_messages_handles_timeout(
    consumer: DualWriteReconcilerConsumer,
) -> None:
    """Test that _poll_messages() handles TimeoutError gracefully."""
    # Arrange: Mock subscription that raises TimeoutError, then CancelledError to break loop
    call_count = 0

    async def mock_fetch(*args: Any, **kwargs: Any) -> list:
        nonlocal call_count
        await asyncio.sleep(0)  # Make function properly async
        call_count += 1
        if call_count == 1:
            raise TimeoutError("No messages")
        else:
            raise asyncio.CancelledError()  # Break loop

    mock_subscription = AsyncMock()
    mock_subscription.fetch = mock_fetch
    consumer._subscription = mock_subscription

    # Act & Assert: Should raise CancelledError after handling timeout
    with pytest.raises(asyncio.CancelledError):
        await consumer._poll_messages()

    # Assert: Fetch was called multiple times (timeout handled, loop continued)
    assert call_count >= 2


@pytest.mark.asyncio
async def test_poll_messages_processes_messages(
    consumer: DualWriteReconcilerConsumer,
    mock_reconciliation_service: AsyncMock,
) -> None:
    """Test that _poll_messages() processes messages from fetch."""
    mock_subscription = AsyncMock()
    mock_msg = AsyncMock()
    mock_msg.data = Mock()

    envelope = EventEnvelope(
        event_type="planning.dualwrite.reconcile.requested",
        payload={
            "operation_id": "op-123",
            "operation_type": "save_story",
            "operation_data": {"story_id": "ST-1"},
        },
        idempotency_key="idemp-test",
        correlation_id="corr-test",
        timestamp="2025-12-30T10:00:00+00:00",
        producer="planning-service",
    )
    mock_msg.data.decode.return_value = json.dumps(EventEnvelopeMapper.to_dict(envelope))

    # Arrange: First call returns message, second call raises CancelledError to break loop
    call_count = 0

    async def mock_fetch(*args: Any, **kwargs: Any) -> list:
        nonlocal call_count
        await asyncio.sleep(0)  # Make function properly async
        call_count += 1
        if call_count == 1:
            return [mock_msg]
        else:
            raise asyncio.CancelledError()  # Break loop

    mock_subscription.fetch = mock_fetch
    consumer._subscription = mock_subscription

    # Act & Assert: Should raise CancelledError after processing message
    with pytest.raises(asyncio.CancelledError):
        await consumer._poll_messages()

    # Verify message was processed
    mock_reconciliation_service.reconcile_operation.assert_awaited_once_with(
        operation_id="op-123",
        operation_type="save_story",
        operation_data={"story_id": "ST-1"},
    )
    mock_msg.ack.assert_awaited_once()
