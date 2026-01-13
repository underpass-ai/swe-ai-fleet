"""Unit tests for AuditPendingOperationsUseCase."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from planning.application.dto.dual_write_operation import (
    DualWriteOperation,
    DualWriteStatus,
)
from planning.application.ports.dual_write_ledger_port import DualWriteLedgerPort
from planning.application.ports.messaging_port import MessagingPort
from planning.application.ports.metrics_port import MetricsPort
from planning.application.usecases.audit_pending_operations_usecase import (
    AuditPendingOperationsUseCase,
)


@pytest.fixture
def mock_ledger() -> AsyncMock:
    """Create mock dual write ledger port."""
    return AsyncMock(spec=DualWriteLedgerPort)


@pytest.fixture
def mock_messaging() -> AsyncMock:
    """Create mock messaging port."""
    return AsyncMock(spec=MessagingPort)


@pytest.fixture
def mock_metrics() -> AsyncMock:
    """Create mock metrics port."""
    return AsyncMock(spec=MetricsPort)


@pytest.fixture
def use_case(
    mock_ledger: AsyncMock,
    mock_messaging: AsyncMock,
    mock_metrics: AsyncMock,
) -> AuditPendingOperationsUseCase:
    """Create audit use case with mocks."""
    return AuditPendingOperationsUseCase(
        dual_write_ledger=mock_ledger,
        messaging=mock_messaging,
        metrics=mock_metrics,
        age_threshold_seconds=300.0,
    )


@pytest.fixture
def old_operation() -> DualWriteOperation:
    """Create old PENDING operation (10 minutes ago)."""
    now = datetime.now(UTC)
    old_time = now - timedelta(minutes=10)
    return DualWriteOperation(
        operation_id="op-123",
        status=DualWriteStatus.PENDING,
        attempts=2,
        last_error="Neo4j connection failed",
        created_at=old_time.isoformat(),
        updated_at=old_time.isoformat(),
    )


@pytest.fixture
def recent_operation() -> DualWriteOperation:
    """Create recent PENDING operation (1 minute ago)."""
    now = datetime.now(UTC)
    recent_time = now - timedelta(minutes=1)
    return DualWriteOperation(
        operation_id="op-456",
        status=DualWriteStatus.PENDING,
        attempts=0,
        last_error=None,
        created_at=recent_time.isoformat(),
        updated_at=recent_time.isoformat(),
    )


@pytest.mark.asyncio
async def test_execute_no_pending_operations(
    use_case: AuditPendingOperationsUseCase,
    mock_ledger: AsyncMock,
    mock_metrics: AsyncMock,
) -> None:
    """Test audit with no pending operations."""
    mock_ledger.list_pending_operations.return_value = []

    results = await use_case.execute()

    assert results["total_pending"] == 0
    assert results["old_pending"] == 0
    assert results["republished"] == 0
    assert results["max_age_seconds"] == 0.0

    mock_ledger.list_pending_operations.assert_awaited_once_with(limit=1000)
    mock_ledger.list_old_pending_operations.assert_awaited_once_with(
        age_seconds=300.0, limit=100
    )
    mock_metrics.record_pending_count.assert_called_once_with(0)


@pytest.mark.asyncio
async def test_execute_with_old_pending_operations(
    use_case: AuditPendingOperationsUseCase,
    mock_ledger: AsyncMock,
    mock_messaging: AsyncMock,
    mock_metrics: AsyncMock,
    old_operation: DualWriteOperation,
    recent_operation: DualWriteOperation,
) -> None:
    """Test audit with old pending operations."""
    # All pending operations
    mock_ledger.list_pending_operations.return_value = [
        old_operation,
        recent_operation,
    ]

    # Old pending operations (older than 5 minutes)
    mock_ledger.list_old_pending_operations.return_value = [old_operation]

    results = await use_case.execute()

    assert results["total_pending"] == 2
    assert results["old_pending"] == 1
    assert results["republished"] == 1
    assert results["max_age_seconds"] > 500.0  # ~10 minutes = 600 seconds

    mock_messaging.publish_dualwrite_reconcile_requested.assert_awaited_once_with(
        operation_id="op-123",
        operation_type="unknown",
        operation_data={},
    )
    mock_metrics.increment_reconcile_attempts.assert_called_once()


@pytest.mark.asyncio
async def test_execute_without_metrics(
    mock_ledger: AsyncMock,
    mock_messaging: AsyncMock,
    old_operation: DualWriteOperation,
) -> None:
    """Test audit without metrics port."""
    use_case = AuditPendingOperationsUseCase(
        dual_write_ledger=mock_ledger,
        messaging=mock_messaging,
        metrics=None,
        age_threshold_seconds=300.0,
    )

    mock_ledger.list_pending_operations.return_value = [old_operation]
    mock_ledger.list_old_pending_operations.return_value = [old_operation]

    results = await use_case.execute()

    assert results["total_pending"] == 1
    assert results["old_pending"] == 1
    assert results["republished"] == 1

    # Should not raise exception even without metrics
    mock_messaging.publish_dualwrite_reconcile_requested.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_republish_error_continues(
    use_case: AuditPendingOperationsUseCase,
    mock_ledger: AsyncMock,
    mock_messaging: AsyncMock,
    old_operation: DualWriteOperation,
) -> None:
    """Test audit continues on republish error."""
    mock_ledger.list_pending_operations.return_value = [old_operation]
    mock_ledger.list_old_pending_operations.return_value = [old_operation]

    # Simulate republish error
    mock_messaging.publish_dualwrite_reconcile_requested.side_effect = Exception(
        "NATS connection failed"
    )

    results = await use_case.execute()

    assert results["total_pending"] == 1
    assert results["old_pending"] == 1
    assert results["republished"] == 0  # Failed to republish


@pytest.mark.asyncio
async def test_calculate_age(
    use_case: AuditPendingOperationsUseCase,
    old_operation: DualWriteOperation,
) -> None:
    """Test age calculation."""
    now = datetime.now(UTC)
    age = use_case._calculate_age(old_operation, now)
    assert age > 500.0  # ~10 minutes
    assert age < 700.0  # Less than 12 minutes


@pytest.mark.asyncio
async def test_calculate_age_invalid_timestamp(
    use_case: AuditPendingOperationsUseCase,
) -> None:
    """Test age calculation with invalid timestamp."""
    from unittest.mock import MagicMock

    # Create a mock operation with invalid timestamp
    # We can't create a real DualWriteOperation with invalid timestamp
    # because it validates in __post_init__, so we use a mock
    operation = MagicMock(spec=DualWriteOperation)
    operation.operation_id = "op-invalid"
    operation.created_at = "invalid-timestamp"

    now = datetime.now(UTC)
    age = use_case._calculate_age(operation, now)
    assert age == 0.0  # Returns 0 on error
