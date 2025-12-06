"""Unit tests for BacklogReviewResultConsumer."""

import asyncio
import json
from unittest.mock import AsyncMock, Mock

import pytest
from planning.application.usecases import ProcessStoryReviewResultUseCase
from planning.infrastructure.consumers.backlog_review_result_consumer import (
    BacklogReviewResultConsumer,
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
def mock_process_review_result():
    """Mock ProcessStoryReviewResultUseCase."""
    return AsyncMock(spec=ProcessStoryReviewResultUseCase)


@pytest.fixture
def consumer(mock_nats_client, mock_jetstream, mock_process_review_result):
    """Create BacklogReviewResultConsumer instance."""
    return BacklogReviewResultConsumer(
        nats_client=mock_nats_client,
        jetstream=mock_jetstream,
        process_review_result=mock_process_review_result,
    )


@pytest.mark.asyncio
async def test_stop_cancels_polling_task_and_raises_cancelled_error(consumer):
    """Test that stop() cancels the polling task and re-raises CancelledError.

    This is a critical test ensuring asyncio cancellation propagation works correctly.
    The stop() method MUST re-raise CancelledError after cleanup.
    """
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
async def test_stop_handles_no_polling_task(consumer):
    """Test that stop() handles case where no polling task exists."""
    consumer._polling_task = None

    # Act: Should not raise when no polling task exists
    await consumer.stop()

    # Assert: Consumer stopped successfully
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

    # Give the task a moment to start
    await asyncio.sleep(0.01)

    # Act & Assert: Should raise CancelledError
    with pytest.raises(asyncio.CancelledError):
        await consumer.stop()

    # Assert: Logging message should be present
    assert "BacklogReviewResultConsumer stopped" in caplog.text


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
    # Note: Don't await cancelled task in test cleanup - just cancel it


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
async def test_handle_message_processes_successful_review(consumer, mock_process_review_result):
    """Test that _handle_message() processes successful review result."""
    # Arrange: Create mock message with valid review result
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = json.dumps({
        "task_id": "ceremony-abc123:story-ST-456:role-ARCHITECT",
        "agent_id": "ARCHITECT-agent-1",
        "role": "ARCHITECT",
        "proposal": "Technical feedback for the story",
        "operations": None,
        "duration_ms": 45000,
        "is_success": True,
        "error_message": None,
        "model": "Qwen/Qwen3-0.6B",
        "timestamp": "2025-12-02T10:30:00Z"
    })

    # Act
    await consumer._handle_message(mock_msg)

    # Assert: Use case called
    mock_process_review_result.execute.assert_awaited_once()

    # Assert: Message ACKed
    mock_msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_skips_failed_agent_result(consumer, mock_process_review_result):
    """Test that _handle_message() skips failed agent results."""
    # Arrange: Create mock message with failed agent result
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = json.dumps({
        "task_id": "ceremony-abc123:story-ST-456:role-ARCHITECT",
        "agent_id": "ARCHITECT-agent-1",
        "role": "ARCHITECT",
        "is_success": False,
        "error_message": "LLM failed",
        "timestamp": "2025-12-02T10:30:00Z"
    })

    # Act
    await consumer._handle_message(mock_msg)

    # Assert: Use case NOT called
    mock_process_review_result.execute.assert_not_awaited()

    # Assert: Message ACKed (don't retry failed agents)
    mock_msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_handles_invalid_task_id_format(consumer, mock_process_review_result):
    """Test that _handle_message() handles invalid task_id format."""
    # Arrange: Create mock message with invalid task_id
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = json.dumps({
        "task_id": "invalid-format",
        "is_success": True,
        "proposal": "Feedback",
        "timestamp": "2025-12-02T10:30:00Z"
    })

    # Act
    await consumer._handle_message(mock_msg)

    # Assert: Use case NOT called
    mock_process_review_result.execute.assert_not_awaited()

    # Assert: Message NAKed (retry)
    mock_msg.nak.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_handles_json_decode_error(consumer, mock_process_review_result):
    """Test that _handle_message() handles invalid JSON."""
    # Arrange: Create mock message with invalid JSON
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = "invalid json"

    # Act
    await consumer._handle_message(mock_msg)

    # Assert: Use case NOT called
    mock_process_review_result.execute.assert_not_awaited()

    # Assert: Message NAKed
    mock_msg.nak.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_handles_use_case_exception(consumer, mock_process_review_result):
    """Test that _handle_message() handles exceptions from use case."""
    # Arrange: Create mock message with valid payload
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = json.dumps({
        "task_id": "ceremony-abc123:story-ST-456:role-ARCHITECT",
        "agent_id": "ARCHITECT-agent-1",
        "role": "ARCHITECT",
        "proposal": "Feedback",
        "is_success": True,
        "timestamp": "2025-12-02T10:30:00Z"
    })

    # Mock use case to raise exception
    mock_process_review_result.execute.side_effect = Exception("Database error")

    # Act
    await consumer._handle_message(mock_msg)

    # Assert: Message NAKed (retry)
    mock_msg.nak.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancellation_propagation_through_stop_method(consumer):
    """Integration test: Verify CancelledError propagates correctly through stop().

    This test simulates real cancellation scenario where:
    1. Consumer is started
    2. Polling task is running
    3. stop() is called (e.g., during graceful shutdown)
    4. CancelledError must propagate to allow proper cleanup
    """
    # Arrange: Mock subscription to keep polling alive
    mock_subscription = AsyncMock()

    async def mock_fetch(*args, **kwargs):
        await asyncio.sleep(0.1)
        raise TimeoutError("No messages")

    mock_subscription.fetch = mock_fetch
    consumer._subscription = mock_subscription

    # Start background polling
    consumer._polling_task = asyncio.create_task(consumer._poll_messages())

    # Give polling task time to start
    await asyncio.sleep(0.01)

    # Act & Assert: stop() must re-raise CancelledError
    with pytest.raises(asyncio.CancelledError):
        await consumer.stop()

    # Assert: Task is cancelled
    assert consumer._polling_task.cancelled()
