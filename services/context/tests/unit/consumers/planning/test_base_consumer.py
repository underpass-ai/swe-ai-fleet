"""Unit tests for BasePlanningConsumer."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from services.context.consumers.planning.base_consumer import BasePlanningConsumer


class ConcreteConsumer(BasePlanningConsumer):
    """Concrete implementation for testing."""

    async def start(self) -> None:
        """Start consuming (test implementation)."""
        self._subscription = Mock()
        self._polling_task = asyncio.create_task(
            self._poll_messages(self._subscription, self._handle_message)
        )

    async def _handle_message(self, msg) -> None:
        """Handle message (test implementation)."""
        await msg.ack()


@pytest.mark.asyncio
async def test_process_message_batch_success():
    """Test successful batch processing."""
    # Arrange
    mock_js = AsyncMock()
    mock_graph = AsyncMock()
    consumer = ConcreteConsumer(
        js=mock_js,
        graph_command=mock_graph,
        cache_service=None,
    )

    # Create mock messages
    msg1 = Mock()
    msg1.ack = AsyncMock()
    msg2 = Mock()
    msg2.ack = AsyncMock()
    msgs = [msg1, msg2]

    async def mock_handler(msg):
        await msg.ack()

    # Act
    await consumer._process_message_batch(msgs, mock_handler, "TestConsumer")

    # Assert
    msg1.ack.assert_awaited_once()
    msg2.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_message_batch_handles_individual_errors():
    """Test that errors in individual messages don't stop batch processing."""
    # Arrange
    mock_js = AsyncMock()
    mock_graph = AsyncMock()
    consumer = ConcreteConsumer(
        js=mock_js,
        graph_command=mock_graph,
        cache_service=None,
    )

    # First message fails, second succeeds
    msg1 = Mock()
    msg1.ack = AsyncMock(side_effect=Exception("Processing error"))
    msg2 = Mock()
    msg2.ack = AsyncMock()
    msgs = [msg1, msg2]

    async def mock_handler(msg):
        await msg.ack()

    # Act - should not raise, just log error
    await consumer._process_message_batch(msgs, mock_handler, "TestConsumer")

    # Assert - second message should still be processed
    msg2.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_polling_error_returns_incremented_count():
    """Test that polling error increments error count."""
    # Arrange
    mock_js = AsyncMock()
    mock_graph = AsyncMock()
    consumer = ConcreteConsumer(
        js=mock_js,
        graph_command=mock_graph,
        cache_service=None,
    )

    # Act
    new_error_count, new_backoff = await consumer._handle_polling_error(
        error=Exception("Test error"),
        error_count=2,
        max_errors=5,
        backoff_seconds=1,
        consumer_name="TestConsumer",
    )

    # Assert
    assert new_error_count == 3
    assert new_backoff == 1  # Should not change yet


@pytest.mark.asyncio
async def test_handle_polling_error_triggers_backoff_at_max():
    """Test that reaching max errors triggers exponential backoff."""
    # Arrange
    mock_js = AsyncMock()
    mock_graph = AsyncMock()
    consumer = ConcreteConsumer(
        js=mock_js,
        graph_command=mock_graph,
        cache_service=None,
    )

    # Act - simulate reaching max errors (5)
    with patch("asyncio.sleep") as mock_sleep:
        new_error_count, new_backoff = await consumer._handle_polling_error(
            error=Exception("Test error"),
            error_count=5,
            max_errors=5,
            backoff_seconds=4,
            consumer_name="TestConsumer",
        )

    # Assert
    assert new_error_count == 0  # Reset after backoff
    assert new_backoff == 8  # Doubled (4 * 2)
    mock_sleep.assert_awaited_once_with(4)


@pytest.mark.asyncio
async def test_handle_polling_error_caps_backoff_at_60s():
    """Test that backoff is capped at 60 seconds."""
    # Arrange
    mock_js = AsyncMock()
    mock_graph = AsyncMock()
    consumer = ConcreteConsumer(
        js=mock_js,
        graph_command=mock_graph,
        cache_service=None,
    )

    # Act - trigger backoff with 50 seconds (would become 100)
    with patch("asyncio.sleep") as mock_sleep:
        _, new_backoff = await consumer._handle_polling_error(
            error=Exception("Test error"),
            error_count=5,
            max_errors=5,
            backoff_seconds=50,
            consumer_name="TestConsumer",
        )

    # Assert
    assert new_backoff == 60  # Capped at max
    mock_sleep.assert_awaited_once_with(50)


@pytest.mark.asyncio
async def test_stop_cancels_polling_task():
    """Test that stop() cancels the polling task."""
    # Arrange
    mock_js = AsyncMock()
    mock_graph = AsyncMock()
    consumer = ConcreteConsumer(
        js=mock_js,
        graph_command=mock_graph,
        cache_service=None,
    )

    # Create a fake polling task
    async def fake_polling():
        await asyncio.sleep(100)  # Long sleep to simulate polling

    consumer._polling_task = asyncio.create_task(fake_polling())

    # Act & Assert - should re-raise CancelledError
    with pytest.raises(asyncio.CancelledError):
        await consumer.stop()

    # Task should be cancelled
    assert consumer._polling_task.cancelled()


@pytest.mark.asyncio
async def test_stop_handles_no_polling_task():
    """Test that stop() handles case where no polling task exists."""
    # Arrange
    mock_js = AsyncMock()
    mock_graph = AsyncMock()
    consumer = ConcreteConsumer(
        js=mock_js,
        graph_command=mock_graph,
        cache_service=None,
    )

    consumer._polling_task = None

    # Act - should not raise
    await consumer.stop()

    # No assertion needed - just verify it doesn't crash


@pytest.mark.asyncio
async def test_poll_messages_resets_errors_on_success():
    """Test that successful batch resets error count."""
    # Arrange
    mock_js = AsyncMock()
    mock_graph = AsyncMock()
    consumer = ConcreteConsumer(
        js=mock_js,
        graph_command=mock_graph,
        cache_service=None,
    )

    # Mock subscription that returns messages once, then stops
    mock_subscription = Mock()
    call_count = 0

    async def mock_fetch(batch, timeout):
        await asyncio.sleep(0)  # Make function truly async
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Return messages on first call
            msg = Mock()
            msg.ack = AsyncMock()
            return [msg]
        else:
            # Raise exception to break loop
            raise KeyboardInterrupt()

    mock_subscription.fetch = mock_fetch

    async def noop_handler(msg):
        await msg.ack()

    # Act
    with pytest.raises(KeyboardInterrupt):
        await consumer._poll_messages(mock_subscription, noop_handler, batch_size=1)

    # No explicit assertion - just verify it processes without error


@pytest.mark.asyncio
async def test_poll_messages_handles_timeout():
    """Test that timeout exception continues polling."""
    # Arrange
    mock_js = AsyncMock()
    mock_graph = AsyncMock()
    consumer = ConcreteConsumer(
        js=mock_js,
        graph_command=mock_graph,
        cache_service=None,
    )

    # Mock subscription that times out twice, then raises to break loop
    mock_subscription = Mock()
    call_count = 0

    async def mock_fetch(batch, timeout):
        await asyncio.sleep(0)  # Make function truly async
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise TimeoutError()
        else:
            raise KeyboardInterrupt()  # Break loop

    mock_subscription.fetch = mock_fetch

    async def noop_handler(msg):
        pass

    # Act
    with pytest.raises(KeyboardInterrupt):
        await consumer._poll_messages(mock_subscription, noop_handler)

    # Assert - should have tried 3 times (2 timeouts + 1 interrupt)
    assert call_count == 3


def test_base_consumer_initialization():
    """Test BasePlanningConsumer initialization."""
    # Arrange
    mock_js = Mock()
    mock_graph = Mock()
    mock_cache = Mock()

    # Act
    consumer = ConcreteConsumer(
        js=mock_js,
        graph_command=mock_graph,
        cache_service=mock_cache,
    )

    # Assert
    assert consumer.js == mock_js
    assert consumer.graph == mock_graph
    assert consumer.cache == mock_cache
    assert consumer._subscription is None
    assert consumer._polling_task is None


def test_base_consumer_initialization_without_cache():
    """Test BasePlanningConsumer initialization without optional cache."""
    # Arrange
    mock_js = Mock()
    mock_graph = Mock()

    # Act
    consumer = ConcreteConsumer(
        js=mock_js,
        graph_command=mock_graph,
        cache_service=None,
    )

    # Assert
    assert consumer.js == mock_js
    assert consumer.graph == mock_graph
    assert consumer.cache is None


@pytest.mark.asyncio
async def test_start_raises_not_implemented():
    """Test that base class start() raises NotImplementedError."""
    # Arrange
    mock_js = AsyncMock()
    mock_graph = AsyncMock()
    consumer = BasePlanningConsumer(
        js=mock_js,
        graph_command=mock_graph,
        cache_service=None,
    )

    # Act & Assert
    with pytest.raises(NotImplementedError, match="Subclasses must implement start"):
        await consumer.start()


@pytest.mark.asyncio
async def test_handle_message_raises_not_implemented():
    """Test that base class _handle_message() raises NotImplementedError."""
    # Arrange
    mock_js = AsyncMock()
    mock_graph = AsyncMock()
    consumer = BasePlanningConsumer(
        js=mock_js,
        graph_command=mock_graph,
        cache_service=None,
    )

    msg = Mock()

    # Act & Assert
    with pytest.raises(NotImplementedError, match="Subclasses must implement _handle_message"):
        await consumer._handle_message(msg)

