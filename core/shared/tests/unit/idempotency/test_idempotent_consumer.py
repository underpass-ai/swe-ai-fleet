"""Unit tests for idempotent_consumer middleware.

Tests use mocks to avoid hitting real storage or executing real handlers.
Following repository rules: unit tests MUST NOT hit external systems.
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.shared.events.event_envelope import EventEnvelope
from core.shared.idempotency.idempotency_port import IdempotencyPort
from core.shared.idempotency.idempotency_state import IdempotencyState
from core.shared.idempotency.middleware.idempotent_consumer import (
    extract_idempotency_key_from_envelope,
    idempotent_consumer,
)


class MockIdempotencyPort:
    """Mock implementation of IdempotencyPort for testing."""

    def __init__(self):
        self._states: dict[str, IdempotencyState] = {}
        self._timestamps: dict[str, str] = {}
        self.check_status = AsyncMock(side_effect=self._check_status)
        self.mark_in_progress = AsyncMock(side_effect=self._mark_in_progress)
        self.mark_completed = AsyncMock(side_effect=self._mark_completed)
        self.is_stale = AsyncMock(side_effect=self._is_stale)

    async def _check_status(self, idempotency_key: str) -> IdempotencyState | None:
        return self._states.get(idempotency_key)

    async def _mark_in_progress(self, idempotency_key: str, ttl_seconds: int) -> bool:
        if idempotency_key in self._states:
            return False  # Already exists
        self._states[idempotency_key] = IdempotencyState.IN_PROGRESS
        self._timestamps[idempotency_key] = datetime.now(timezone.utc).isoformat()
        return True

    async def _mark_completed(self, idempotency_key: str, ttl_seconds: int | None = None) -> None:
        self._states[idempotency_key] = IdempotencyState.COMPLETED
        self._timestamps[idempotency_key] = datetime.now(timezone.utc).isoformat()

    async def _is_stale(self, idempotency_key: str, max_age_seconds: int) -> bool:
        if idempotency_key not in self._states:
            return False
        if self._states[idempotency_key] != IdempotencyState.IN_PROGRESS:
            return False
        # Simple stale check: if timestamp exists, consider it fresh for tests
        return False  # Not stale by default in tests


class TestIdempotentConsumer:
    """Test cases for idempotent_consumer decorator."""

    @pytest.fixture
    def mock_port(self):
        """Create mock idempotency port."""
        return MockIdempotencyPort()

    @pytest.fixture
    def mock_handler(self):
        """Create mock handler function."""
        return AsyncMock()

    @pytest.fixture
    def mock_msg(self):
        """Create mock NATS message with EventEnvelope."""
        envelope = EventEnvelope(
            event_type="test.event",
            payload={"test": "data"},
            idempotency_key="test-key-123",
            correlation_id="corr-123",
            timestamp=datetime.now(timezone.utc).isoformat(),
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

    def test_extract_idempotency_key_from_envelope(self, mock_msg):
        """Test extract_idempotency_key_from_envelope helper."""
        key = extract_idempotency_key_from_envelope(mock_msg)

        assert key == "test-key-123"

    def test_extract_idempotency_key_invalid_envelope(self):
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

        # Mock is_stale to return True
        async def mock_is_stale(key: str, max_age: int) -> bool:
            return True

        mock_port.is_stale = AsyncMock(side_effect=mock_is_stale)

        # Mock mark_in_progress to allow overwriting stale state
        # First call fails (key exists), but we want to allow retry for stale
        # So we'll make it succeed on second call by clearing the state first
        original_mark = mock_port._mark_in_progress

        async def mock_mark_in_progress(key: str, ttl: int) -> bool:
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

        await decorated(mock_msg)

        # Handler should be called (fallback without idempotency)
        mock_handler.assert_awaited_once_with(mock_msg)

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

    def test_idempotent_consumer_invalid_ttl(self, mock_port):
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
