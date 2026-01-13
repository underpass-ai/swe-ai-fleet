"""Unit tests for DualWriteAuditJob."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from planning.application.usecases.audit_pending_operations_usecase import (
    AuditPendingOperationsUseCase,
)
from planning.infrastructure.workers.dual_write_audit_job import DualWriteAuditJob


@pytest.fixture
def mock_use_case() -> AsyncMock:
    """Create mock audit use case."""
    return AsyncMock(spec=AuditPendingOperationsUseCase)


@pytest.fixture
def audit_job(mock_use_case: AsyncMock) -> DualWriteAuditJob:
    """Create audit job with mock use case."""
    return DualWriteAuditJob(
        audit_use_case=mock_use_case,
        interval_seconds=0.1,  # Fast interval for testing
    )


@pytest.mark.asyncio
async def test_start_stop(audit_job: DualWriteAuditJob) -> None:
    """Test starting and stopping audit job."""
    await audit_job.start()

    # Wait a bit for loop to run
    await asyncio.sleep(0.15)

    # stop() re-raises CancelledError after cleanup
    with pytest.raises(asyncio.CancelledError):
        await audit_job.stop()

    # Verify use case was called
    assert audit_job._use_case.execute.await_count >= 1


@pytest.mark.asyncio
async def test_start_already_running(audit_job: DualWriteAuditJob) -> None:
    """Test starting already running job."""
    await audit_job.start()

    # Try to start again
    await audit_job.start()  # Should not raise

    # stop() re-raises CancelledError after cleanup
    with pytest.raises(asyncio.CancelledError):
        await audit_job.stop()


@pytest.mark.asyncio
async def test_run_loop_executes_periodically(
    audit_job: DualWriteAuditJob,
    mock_use_case: AsyncMock,
) -> None:
    """Test audit job executes use case periodically."""
    mock_use_case.execute.return_value = {
        "total_pending": 0,
        "old_pending": 0,
        "republished": 0,
        "max_age_seconds": 0.0,
    }

    await audit_job.start()

    # Wait for multiple intervals
    await asyncio.sleep(0.25)

    # stop() re-raises CancelledError after cleanup
    with pytest.raises(asyncio.CancelledError):
        await audit_job.stop()

    # Verify use case was called multiple times
    assert mock_use_case.execute.await_count >= 2


@pytest.mark.asyncio
async def test_run_loop_handles_errors(
    audit_job: DualWriteAuditJob,
    mock_use_case: AsyncMock,
) -> None:
    """Test audit job handles errors gracefully."""
    mock_use_case.execute.side_effect = Exception("Use case error")

    await audit_job.start()

    # Wait for interval
    await asyncio.sleep(0.15)

    # stop() re-raises CancelledError after cleanup
    with pytest.raises(asyncio.CancelledError):
        await audit_job.stop()

    # Verify use case was called (should not crash)
    assert mock_use_case.execute.await_count >= 1


@pytest.mark.asyncio
async def test_stop_cancels_task(audit_job: DualWriteAuditJob) -> None:
    """Test stop cancels background task."""
    await audit_job.start()

    # Verify task exists
    assert audit_job._task is not None
    assert not audit_job._task.done()

    # stop() re-raises CancelledError after cleanup
    with pytest.raises(asyncio.CancelledError):
        await audit_job.stop()

    # Verify task is cancelled
    assert audit_job._task.done()
