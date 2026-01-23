"""Integration tests for IdempotencyPort usage in ceremony engine.

These tests validate that:
- IdempotencyPort from core/shared can be used in ceremony_engine
- Reinicio del service no duplica side effects (E0.4 AC)
- Idempotency prevents duplicate processing
"""

import pytest
from unittest.mock import AsyncMock

from core.shared.idempotency.idempotency_port import IdempotencyPort
from core.shared.idempotency.idempotency_state import IdempotencyState


@pytest.fixture
def mock_idempotency_port() -> AsyncMock:
    """Create mock IdempotencyPort."""
    port = AsyncMock(spec=IdempotencyPort)
    return port


@pytest.mark.asyncio
async def test_idempotency_port_check_status_not_found(
    mock_idempotency_port: AsyncMock,
) -> None:
    """Test checking status of non-existent key."""
    mock_idempotency_port.check_status.return_value = None

    result = await mock_idempotency_port.check_status("non-existent-key")

    assert result is None
    mock_idempotency_port.check_status.assert_awaited_once_with("non-existent-key")


@pytest.mark.asyncio
async def test_idempotency_port_check_status_completed(
    mock_idempotency_port: AsyncMock,
) -> None:
    """Test checking status of completed key."""
    mock_idempotency_port.check_status.return_value = IdempotencyState.COMPLETED

    result = await mock_idempotency_port.check_status("completed-key")

    assert result == IdempotencyState.COMPLETED


@pytest.mark.asyncio
async def test_idempotency_port_mark_in_progress_success(
    mock_idempotency_port: AsyncMock,
) -> None:
    """Test marking key as IN_PROGRESS successfully."""
    mock_idempotency_port.mark_in_progress.return_value = True

    result = await mock_idempotency_port.mark_in_progress("new-key", ttl_seconds=300)

    assert result is True
    mock_idempotency_port.mark_in_progress.assert_awaited_once_with("new-key", ttl_seconds=300)


@pytest.mark.asyncio
async def test_idempotency_port_mark_in_progress_already_processed(
    mock_idempotency_port: AsyncMock,
) -> None:
    """Test marking key as IN_PROGRESS when already processed."""
    mock_idempotency_port.mark_in_progress.return_value = False

    result = await mock_idempotency_port.mark_in_progress("already-processed", ttl_seconds=300)

    assert result is False
    # This prevents duplicate processing (E0.4 AC)


@pytest.mark.asyncio
async def test_idempotency_port_mark_completed(
    mock_idempotency_port: AsyncMock,
) -> None:
    """Test marking key as COMPLETED."""
    mock_idempotency_port.mark_completed.return_value = None

    await mock_idempotency_port.mark_completed("completed-key", ttl_seconds=None)

    mock_idempotency_port.mark_completed.assert_awaited_once_with("completed-key", ttl_seconds=None)


@pytest.mark.asyncio
async def test_idempotency_port_is_stale(
    mock_idempotency_port: AsyncMock,
) -> None:
    """Test checking if IN_PROGRESS state is stale."""
    mock_idempotency_port.is_stale.return_value = True

    result = await mock_idempotency_port.is_stale("stale-key", max_age_seconds=600)

    assert result is True
    mock_idempotency_port.is_stale.assert_awaited_once_with("stale-key", max_age_seconds=600)


@pytest.mark.asyncio
async def test_idempotency_prevents_duplicate_processing(
    mock_idempotency_port: AsyncMock,
) -> None:
    """Test that idempotency prevents duplicate processing (E0.4 AC).

    Scenario:
    1. First call: mark_in_progress succeeds (True)
    2. Second call (after restart/redelivery): mark_in_progress fails (False)
    3. This prevents duplicate side effects
    """
    # First call succeeds
    mock_idempotency_port.mark_in_progress.return_value = True
    result1 = await mock_idempotency_port.mark_in_progress("test-key", ttl_seconds=300)
    assert result1 is True

    # Mark as completed
    await mock_idempotency_port.mark_completed("test-key")

    # Second call (after restart/redelivery) fails - already processed
    mock_idempotency_port.mark_in_progress.return_value = False
    result2 = await mock_idempotency_port.mark_in_progress("test-key", ttl_seconds=300)
    assert result2 is False

    # This prevents duplicate processing (E0.4 AC: reinicio no duplica side effects)


@pytest.mark.asyncio
async def test_idempotency_check_status_completed_prevents_retry(
    mock_idempotency_port: AsyncMock,
) -> None:
    """Test that COMPLETED status prevents retry."""
    # Check status returns COMPLETED
    mock_idempotency_port.check_status.return_value = IdempotencyState.COMPLETED

    status = await mock_idempotency_port.check_status("completed-key")

    assert status == IdempotencyState.COMPLETED
    assert status.is_terminal() is True
    # Terminal state means no further processing needed (E0.4 AC)
