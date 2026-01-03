"""Unit tests for idempotent_consumer middleware.

Tests use mocks to avoid hitting real storage or executing real handlers.
Following repository rules: unit tests MUST NOT hit external systems.
"""

import asyncio
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.shared.events.event_envelope import EventEnvelope
from core.shared.idempotency.idempotency_state import IdempotencyState
from core.shared.idempotency.middleware.idempotent_consumer import (
    extract_idempotency_key_from_envelope,
    idempotent_consumer,
)


class MockIdempotencyPort:
    """Mock implementation of IdempotencyPort for testing."""

    def __init__(self) -> None:
        self._states: dict[str, IdempotencyState] = {}
        self._timestamps: dict[str, str] = {}
        self.check_status = AsyncMock(side_effect=self._check_status)
        self.mark_in_progress = AsyncMock(side_effect=self._mark_in_progress)
        self.mark_completed = AsyncMock(side_effect=self._mark_completed)
        self.is_stale = AsyncMock(side_effect=self._is_stale)

    async def _check_status(self, idempotency_key: str) -> IdempotencyState | None:
        await asyncio.sleep(0)  # Make function truly async
        return self._states.get(idempotency_key)

    async def _mark_in_progress(self, idempotency_key: str, ttl_seconds: int) -> bool:
        await asyncio.sleep(0)  # Make function truly async
        if idempotency_key in self._states:
            return False  # Already exists
        self._states[idempotency_key] = IdempotencyState.IN_PROGRESS
        self._timestamps[idempotency_key] = datetime.now(UTC).isoformat()
        return True

    async def _mark_completed(self, idempotency_key: str, ttl_seconds: int | None = None) -> None:
        await asyncio.sleep(0)  # Make function truly async
        self._states[idempotency_key] = IdempotencyState.COMPLETED
        self._timestamps[idempotency_key] = datetime.now(UTC).isoformat()

    async def _is_stale(self, idempotency_key: str, max_age_seconds: int) -> bool:
        await asyncio.sleep(0)  # Make function truly async
        if idempotency_key not in self._states:
            return False
        if self._states[idempotency_key] != IdempotencyState.IN_PROGRESS:
            return False
        # Check if timestamp is older than max_age_seconds
        if idempotency_key in self._timestamps:
            timestamp_str = self._timestamps[idempotency_key]
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                age_seconds = (datetime.now(UTC) - timestamp).total_seconds()
                return age_seconds > max_age_seconds
            except (ValueError, AttributeError):
                # Invalid timestamp format - consider not stale for tests
                return False
        # No timestamp - consider not stale for tests
        return False


class TestIdempotentConsumer:
    """Test cases for idempotent_consumer decorator."""

    @pytest.fixture
    def mock_port(self) -> MockIdempotencyPort:
        """Create mock idempotency port."""
        return MockIdempotencyPort()

    @pytest.fixture
    def mock_handler(self) -> AsyncMock:
        """Create mock handler function."""
        return AsyncMock()

    @pytest.fixture
    def mock_msg(self) -> MagicMock:
        """Create mock NATS message with EventEnvelope."""
        envelope = EventEnvelope(
            event_type="test.event",
            payload={"test": "data"},
            idempotency_key="test-key-123",
            correlation_id="corr-123",
            timestamp=datetime.now(UTC).isoformat(),
            producer="test-producer",
        )
        data = {
            "event_type": envelope.event_type,
            "payload": envelope.payload,
            "idempotency_key": envelope.idempotency_key,
            "correlation_id": envelope.correlation_id,
            "timestamp": envelope.timestamp,
            "producer": envelope.producer,
        }
        msg = MagicMock()
        msg.data = json.dumps(data).encode("utf-8")
        return msg

    def test_extract_idempotency_key_from_envelope(self, mock_msg: MagicMock) -> None:
        """Test extract_idempotency_key_from_envelope helper."""
        key = extract_idempotency_key_from_envelope(mock_msg)

        assert key == "test-key-123"

    def test_extract_idempotency_key_invalid_envelope(self) -> None:
        """Test extract_idempotency_key_from_envelope with invalid envelope."""
        msg = MagicMock()
        msg.data = json.dumps({"invalid": "data"}).encode("utf-8")

        with pytest.raises(ValueError):
            extract_idempotency_key_from_envelope(msg)

    @pytest.mark.asyncio
    async def test_idempotent_consumer_first_execution(
        self, mock_port, mock_handler, mock_msg
    ):
        """Test idempotent_consumer on first execution (not processed yet)."""
        decorated = idempotent_consumer(
            idempotency_port=mock_port,
            key_fn=extract_idempotency_key_from_envelope,
        )(mock_handler)

        await decorated(mock_msg)

        # Handler should be called
        mock_handler.assert_awaited_once_with(mock_msg)

        # Should mark as IN_PROGRESS and then COMPLETED
        mock_port.mark_in_progress.assert_awaited_once()
        mock_port.mark_completed.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_idempotent_consumer_already_completed(
        self, mock_port, mock_handler, mock_msg
    ):
        """Test idempotent_consumer when message already COMPLETED."""
        # Pre-mark as COMPLETED
        await mock_port._mark_completed("test-key-123")

        decorated = idempotent_consumer(
            idempotency_port=mock_port,
            key_fn=extract_idempotency_key_from_envelope,
        )(mock_handler)

        await decorated(mock_msg)

        # Handler should NOT be called
        mock_handler.assert_not_awaited()

        # Should check status but not mark anything
        mock_port.check_status.assert_awaited()
        mock_port.mark_in_progress.assert_not_awaited()
        mock_port.mark_completed.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_idempotent_consumer_in_progress_not_stale(
        self, mock_port, mock_handler, mock_msg
    ):
        """Test idempotent_consumer when message is IN_PROGRESS (not stale)."""
        # Pre-mark as IN_PROGRESS
        await mock_port._mark_in_progress("test-key-123", ttl_seconds=300)

        decorated = idempotent_consumer(
            idempotency_port=mock_port,
            key_fn=extract_idempotency_key_from_envelope,
        )(mock_handler)

        await decorated(mock_msg)

        # Handler should NOT be called (concurrent processing)
        mock_handler.assert_not_awaited()

        # Should check status and staleness
        mock_port.check_status.assert_awaited()
        mock_port.is_stale.assert_awaited()

    @pytest.mark.asyncio
    async def test_idempotent_consumer_in_progress_stale(
        self, mock_port, mock_handler, mock_msg
    ):
        """Test idempotent_consumer when message is IN_PROGRESS (stale)."""
        # Pre-mark as IN_PROGRESS
        await mock_port._mark_in_progress("test-key-123", ttl_seconds=300)

        # Mock is_stale to return True (for testing stale state)
        async def mock_is_stale(key: str, max_age: int) -> bool:
            await asyncio.sleep(0)  # Make function truly async
            # Return True if key matches test key, False otherwise
            return key == "test-key-123"

        mock_port.is_stale = AsyncMock(side_effect=mock_is_stale)

        # Mock mark_in_progress to allow overwriting stale state
        # First call fails (key exists), but we want to allow retry for stale
        # So we'll make it succeed on second call by clearing the state first
        original_mark = mock_port._mark_in_progress

        async def mock_mark_in_progress(key: str, ttl: int) -> bool:
            await asyncio.sleep(0)  # Make function truly async
            # If key exists and is IN_PROGRESS, clear it first (simulating stale cleanup)
            if key in mock_port._states and mock_port._states[key] == IdempotencyState.IN_PROGRESS:
                del mock_port._states[key]
            return await original_mark(key, ttl)

        mock_port.mark_in_progress = AsyncMock(side_effect=mock_mark_in_progress)

        decorated = idempotent_consumer(
            idempotency_port=mock_port,
            key_fn=extract_idempotency_key_from_envelope,
        )(mock_handler)

        await decorated(mock_msg)

        # Handler should be called (stale state cleared)
        mock_handler.assert_awaited_once_with(mock_msg)

        # Should mark as IN_PROGRESS again and then COMPLETED
        assert mock_port.mark_in_progress.await_count >= 1
        mock_port.mark_completed.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_idempotent_consumer_handler_failure(
        self, mock_port, mock_handler, mock_msg
    ):
        """Test idempotent_consumer when handler raises exception."""
        mock_handler.side_effect = ValueError("Handler error")

        decorated = idempotent_consumer(
            idempotency_port=mock_port,
            key_fn=extract_idempotency_key_from_envelope,
        )(mock_handler)

        with pytest.raises(ValueError, match="Handler error"):
            await decorated(mock_msg)

        # Handler should be called
        mock_handler.assert_awaited_once()

        # Should mark as IN_PROGRESS but NOT COMPLETED
        mock_port.mark_in_progress.assert_awaited_once()
        mock_port.mark_completed.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_idempotent_consumer_no_key_extracted(
        self, mock_port, mock_handler, mock_msg
    ):
        """Test idempotent_consumer when key_fn returns empty string."""
        def empty_key_fn(msg):
            return ""

        decorated = idempotent_consumer(
            idempotency_port=mock_port,
            key_fn=empty_key_fn,
        )(mock_handler)

        with pytest.raises(ValueError, match="idempotency_key is required"):
            await decorated(mock_msg)

        # Handler should NOT be called (no legacy support)
        mock_handler.assert_not_awaited()

        # Should not check status
        mock_port.check_status.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_idempotent_consumer_idempotency_error_fallback(
        self, mock_port, mock_handler, mock_msg
    ):
        """Test idempotent_consumer falls back when idempotency check fails."""
        mock_port.check_status.side_effect = Exception("Storage error")

        decorated = idempotent_consumer(
            idempotency_port=mock_port,
            key_fn=extract_idempotency_key_from_envelope,
        )(mock_handler)

        await decorated(mock_msg)

        # Handler should still be called (fail-open)
        mock_handler.assert_awaited_once_with(mock_msg)

    @pytest.mark.asyncio
    async def test_idempotent_consumer_mark_in_progress_race_condition(
        self, mock_port, mock_handler, mock_msg
    ):
        """Test idempotent_consumer when mark_in_progress returns False (race)."""
        # First call succeeds, second fails (race condition)
        call_count = 0

        async def mock_mark_in_progress(key: str, ttl: int) -> bool:
            await asyncio.sleep(0)  # Make function truly async
            nonlocal call_count
            call_count += 1
            return call_count == 1  # First succeeds, second fails

        mock_port.mark_in_progress = AsyncMock(side_effect=mock_mark_in_progress)

        # Pre-mark as IN_PROGRESS to simulate race
        await mock_port._mark_in_progress("test-key-123", ttl_seconds=300)

        decorated = idempotent_consumer(
            idempotency_port=mock_port,
            key_fn=extract_idempotency_key_from_envelope,
        )(mock_handler)

        await decorated(mock_msg)

        # Handler should NOT be called (race condition detected)
        mock_handler.assert_not_awaited()

    def test_idempotent_consumer_invalid_ttl(self, mock_port: MockIdempotencyPort) -> None:
        """Test idempotent_consumer with invalid TTL raises ValueError."""
        with pytest.raises(ValueError, match="in_progress_ttl_seconds must be positive"):
            idempotent_consumer(
                idempotency_port=mock_port,
                key_fn=extract_idempotency_key_from_envelope,
                in_progress_ttl_seconds=0,
            )

        with pytest.raises(ValueError, match="stale_max_age_seconds must be positive"):
            idempotent_consumer(
                idempotency_port=mock_port,
                key_fn=extract_idempotency_key_from_envelope,
                stale_max_age_seconds=0,
            )

    @pytest.mark.asyncio
    async def test_idempotent_consumer_race_condition_became_completed(
        self, mock_port, mock_handler, mock_msg
    ):
        """Test idempotent_consumer when race condition results in COMPLETED state."""
        # First check_status returns None (not found), then mark_in_progress fails
        # Then second check_status returns COMPLETED
        call_count = 0

        async def mock_check_status(key: str) -> IdempotencyState | None:
            await asyncio.sleep(0)  # Make function truly async
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return None  # First check: not found
            return IdempotencyState.COMPLETED  # Second check after race: COMPLETED

        mock_port.check_status = AsyncMock(side_effect=mock_check_status)

        # mark_in_progress fails (race condition)
        async def mock_mark_in_progress(key: str, ttl: int) -> bool:
            await asyncio.sleep(0)  # Make function truly async
            return False  # Race condition: failed to mark

        mock_port.mark_in_progress = AsyncMock(side_effect=mock_mark_in_progress)

        decorated = idempotent_consumer(
            idempotency_port=mock_port,
            key_fn=extract_idempotency_key_from_envelope,
        )(mock_handler)

        await decorated(mock_msg)

        # Handler should NOT be called (became COMPLETED during race)
        mock_handler.assert_not_awaited()

        # Should have tried to mark and then re-checked
        mock_port.mark_in_progress.assert_awaited_once()
        assert mock_port.check_status.await_count == 2  # Called twice

    @pytest.mark.asyncio
    async def test_idempotent_consumer_race_condition_other_state(
        self, mock_port, mock_handler, mock_msg
    ):
        """Test idempotent_consumer when race condition results in non-COMPLETED state."""
        # First check_status returns None (not found), then mark_in_progress fails
        # Then second check_status returns IN_PROGRESS
        call_count = 0

        async def mock_check_status(key: str) -> IdempotencyState | None:
            await asyncio.sleep(0)  # Make function truly async
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return None  # First check: not found
            return IdempotencyState.IN_PROGRESS  # Second check after race: IN_PROGRESS

        mock_port.check_status = AsyncMock(side_effect=mock_check_status)

        # mark_in_progress fails (race condition)
        async def mock_mark_in_progress(key: str, ttl: int) -> bool:
            await asyncio.sleep(0)  # Make function truly async
            return False  # Race condition: failed to mark

        mock_port.mark_in_progress = AsyncMock(side_effect=mock_mark_in_progress)

        decorated = idempotent_consumer(
            idempotency_port=mock_port,
            key_fn=extract_idempotency_key_from_envelope,
        )(mock_handler)

        await decorated(mock_msg)

        # Handler should NOT be called (already processed)
        mock_handler.assert_not_awaited()

        # Should have tried to mark and then re-checked
        mock_port.mark_in_progress.assert_awaited_once()
        assert mock_port.check_status.await_count == 2  # Called twice

    @pytest.mark.asyncio
    async def test_idempotent_consumer_handler_error_detection(
        self, mock_port, mock_handler, mock_msg
    ):
        """Test idempotent_consumer correctly detects handler errors vs idempotency errors."""
        # The is_handler_error method checks traceback for "Handler failed" or "await handler(msg)"
        # Since the handler raises an error, it will be caught in execute_with_completion
        # and re-raised, which will be caught in wrapped_handler
        mock_handler.side_effect = ValueError("Handler failed")

        decorated = idempotent_consumer(
            idempotency_port=mock_port,
            key_fn=extract_idempotency_key_from_envelope,
        )(mock_handler)

        with pytest.raises(ValueError, match="Handler failed"):
            await decorated(mock_msg)

        # Handler should be called
        mock_handler.assert_awaited_once()

        # Should mark as IN_PROGRESS but NOT COMPLETED
        mock_port.mark_in_progress.assert_awaited_once()
        mock_port.mark_completed.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_idempotent_consumer_class_direct_usage(
        self, mock_port, mock_handler, mock_msg
    ):
        """Test IdempotentConsumer class can be used directly (not just function)."""
        from core.shared.idempotency.middleware.idempotent_consumer import IdempotentConsumer

        consumer = IdempotentConsumer(
            idempotency_port=mock_port,
            key_fn=extract_idempotency_key_from_envelope,
        )

        decorated = consumer(mock_handler)

        await decorated(mock_msg)

        # Handler should be called
        mock_handler.assert_awaited_once_with(mock_msg)

        # Should mark as IN_PROGRESS and then COMPLETED
        mock_port.mark_in_progress.assert_awaited_once()
        mock_port.mark_completed.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_idempotent_consumer_handler_error_with_is_handler_error_true(
        self, mock_port, mock_handler, mock_msg
    ):
        """Test idempotent_consumer when is_handler_error returns True."""
        # Mock is_handler_error to return True to test the handler error path
        from core.shared.idempotency.middleware.idempotent_consumer import _IdempotencyHandler

        # Create a custom exception that will trigger is_handler_error
        # The method checks traceback for "Handler failed" or "await handler(msg)"
        # We'll use a mock that simulates this
        original_is_handler_error = _IdempotencyHandler.is_handler_error

        def mock_is_handler_error(exception: Exception) -> bool:
            # Simulate that the traceback contains "Handler failed"
            # Return True for ValueError exceptions (handler errors), False otherwise
            return isinstance(exception, ValueError)

        # Patch the static method
        _IdempotencyHandler.is_handler_error = staticmethod(mock_is_handler_error)

        try:
            mock_handler.side_effect = ValueError("Some handler error")

            decorated = idempotent_consumer(
                idempotency_port=mock_port,
                key_fn=extract_idempotency_key_from_envelope,
            )(mock_handler)

            with pytest.raises(ValueError, match="Some handler error"):
                await decorated(mock_msg)

            # Handler should be called
            mock_handler.assert_awaited_once()

            # Should mark as IN_PROGRESS but NOT COMPLETED
            mock_port.mark_in_progress.assert_awaited_once()
            mock_port.mark_completed.assert_not_awaited()
        finally:
            # Restore original method
            _IdempotencyHandler.is_handler_error = original_is_handler_error
