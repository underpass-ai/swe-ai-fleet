"""Unit tests for PlanApprovedConsumer."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from planning.application.usecases.derive_tasks_from_plan_usecase import (
    DeriveTasksFromPlanUseCase,
)
from planning.infrastructure.consumers.plan_approved_consumer import (
    PlanApprovedConsumer,
)


@pytest.fixture
def mock_nats_client():
    """Mock NATS client."""
    return Mock()


@pytest.fixture
def mock_jetstream():
    """Mock JetStream context."""
    return AsyncMock()


@pytest.fixture
def mock_derive_tasks_usecase():
    """Mock DeriveTasksFromPlanUseCase."""
    return AsyncMock(spec=DeriveTasksFromPlanUseCase)


@pytest.fixture
def consumer(mock_nats_client, mock_jetstream, mock_derive_tasks_usecase):
    """Create PlanApprovedConsumer instance."""
    return PlanApprovedConsumer(
        nats_client=mock_nats_client,
        jetstream=mock_jetstream,
        derive_tasks_usecase=mock_derive_tasks_usecase,
    )


@pytest.mark.asyncio
async def test_stop_cancels_polling_task_and_raises_cancelled_error(consumer):
    """Test that stop() cancels the polling task and re-raises CancelledError."""
    # Arrange: Create a fake polling task
    async def fake_polling():
        await asyncio.sleep(100)

    consumer._polling_task = asyncio.create_task(fake_polling())

    # Act & Assert: stop() should re-raise CancelledError
    with pytest.raises(asyncio.CancelledError):
        await consumer.stop()

    # Assert: Task should be cancelled
    assert consumer._polling_task.cancelled()


@pytest.mark.asyncio
async def test_stop_handles_no_polling_task(consumer):
    """Test that stop() handles case where no polling task exists."""
    consumer._polling_task = None

    # Act: Should not raise
    await consumer.stop()

    # Assert: Consumer stopped successfully (no exception raised)
    assert consumer._polling_task is None


@pytest.mark.asyncio
async def test_stop_logs_cancellation_before_raising(consumer, caplog):
    """Test that stop() logs cancellation message before re-raising CancelledError."""
    import logging

    caplog.set_level(logging.INFO)

    # Arrange: Create a fake polling task
    async def fake_polling():
        await asyncio.sleep(100)

    consumer._polling_task = asyncio.create_task(fake_polling())

    # Act & Assert: Should raise CancelledError
    with pytest.raises(asyncio.CancelledError):
        await consumer.stop()

    # Assert: Logging message should be present
    assert "PlanApprovedConsumer polling task cancelled" in caplog.text


@pytest.mark.asyncio
async def test_start_creates_subscription_and_starts_polling(consumer, mock_jetstream):
    """Test that start() creates subscription and starts polling task."""
    # Arrange: Mock subscription
    mock_subscription = AsyncMock()
    mock_jetstream.pull_subscribe.return_value = mock_subscription

    # Act
    await consumer.start()

    # Assert: Subscription created
    mock_jetstream.pull_subscribe.assert_awaited_once()

    # Assert: Polling task created
    assert consumer._polling_task is not None

    # Cleanup: Cancel task to avoid hanging
    consumer._polling_task.cancel()
    # Don't await cancelled task - just cancel it to prevent hanging


@pytest.mark.asyncio
async def test_start_raises_exception_on_failure(consumer, mock_jetstream):
    """Test that start() raises exception when subscription fails."""
    # Arrange: Mock subscription failure
    mock_jetstream.pull_subscribe.side_effect = Exception("NATS connection failed")

    # Act & Assert: Should raise exception
    with pytest.raises(Exception, match="NATS connection failed"):
        await consumer.start()

    # Assert: No polling task created on failure
    assert consumer._polling_task is None


@pytest.mark.asyncio
async def test_poll_messages_calls_fetch(consumer):
    """Test that _poll_messages() calls fetch on subscription."""
    # Arrange: Mock subscription
    mock_subscription = AsyncMock()
    mock_subscription.fetch = AsyncMock(side_effect=asyncio.CancelledError())
    consumer._subscription = mock_subscription

    # Act & Assert: Should raise CancelledError when fetch raises it
    with pytest.raises(asyncio.CancelledError):
        await consumer._poll_messages()

    # Assert: Fetch was called
    mock_subscription.fetch.assert_awaited()


@pytest.mark.asyncio
async def test_poll_messages_handles_timeout(consumer):
    """Test that _poll_messages() handles TimeoutError and continues."""
    # Arrange: Mock subscription that raises TimeoutError, then CancelledError
    call_count = 0

    async def mock_fetch(*args, **kwargs):
        nonlocal call_count
        await asyncio.sleep(0)  # Make function truly async
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
async def test_poll_messages_handles_generic_error(consumer):
    """Test that _poll_messages() handles generic errors with backoff."""
    # Arrange: Mock subscription that raises error, then CancelledError
    call_count = 0

    async def mock_fetch(*args, **kwargs):
        nonlocal call_count
        await asyncio.sleep(0)  # Make function truly async
        call_count += 1
        if call_count == 1:
            raise ConnectionError("Connection error")
        else:
            raise asyncio.CancelledError()  # Break loop

    mock_subscription = AsyncMock()
    mock_subscription.fetch = mock_fetch
    consumer._subscription = mock_subscription

    # Arrange: Mock sleep to avoid delays
    with patch(
        "planning.infrastructure.consumers.plan_approved_consumer.asyncio.sleep",
        new_callable=AsyncMock,
    ):
        # Act & Assert: Should raise CancelledError after handling error
        with pytest.raises(asyncio.CancelledError):
            await consumer._poll_messages()

    # Assert: Fetch was called (error handled)
    assert call_count >= 1


@pytest.mark.asyncio
async def test_handle_message_processes_successfully(consumer, mock_derive_tasks_usecase):
    """Test that _handle_message() processes valid message successfully."""
    # Arrange: Create mock message with valid payload
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = '{"plan_id": "plan-001"}'
    mock_derive_tasks_usecase.execute.return_value = "deliberation-123"

    # Act
    await consumer._handle_message(mock_msg)

    # Assert: Use case called with correct plan_id
    from planning.domain.value_objects.identifiers.plan_id import PlanId

    mock_derive_tasks_usecase.execute.assert_awaited_once_with(PlanId("plan-001"))

    # Assert: Message ACKed
    mock_msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_handles_missing_key(consumer):
    """Test that _handle_message() handles KeyError (missing plan_id)."""
    # Arrange: Create mock message with missing plan_id
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = '{"other_field": "value"}'

    # Act
    await consumer._handle_message(mock_msg)

    # Assert: Message NAKed (retry)
    mock_msg.nak.assert_awaited_once()

    # Assert: Use case not called
    consumer._derive_tasks.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_message_handles_invalid_plan_id(consumer):
    """Test that _handle_message() handles ValueError (invalid plan_id)."""
    # Arrange: Create mock message with invalid plan_id (empty string)
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = '{"plan_id": ""}'

    # Act
    await consumer._handle_message(mock_msg)

    # Assert: Message NAKed (retry)
    mock_msg.nak.assert_awaited_once()

    # Assert: Use case not called
    consumer._derive_tasks.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_message_handles_generic_error(consumer, mock_derive_tasks_usecase):
    """Test that _handle_message() handles generic exceptions."""
    # Arrange: Create mock message and make use case raise exception
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = '{"plan_id": "plan-001"}'
    mock_derive_tasks_usecase.execute.side_effect = Exception("Use case error")

    # Act
    await consumer._handle_message(mock_msg)

    # Assert: Message NAKed (retry)
    mock_msg.nak.assert_awaited_once()

    # Assert: Use case was called but failed
    mock_derive_tasks_usecase.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_handles_json_decode_error(consumer):
    """Test that _handle_message() handles invalid JSON."""
    # Arrange: Create mock message with invalid JSON
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = "invalid json"

    # Act
    await consumer._handle_message(mock_msg)

    # Assert: Message NAKed (retry)
    mock_msg.nak.assert_awaited_once()
