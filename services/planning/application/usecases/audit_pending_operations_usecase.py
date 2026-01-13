"""Use case for auditing pending dual write operations.

Following Hexagonal Architecture:
- Application layer use case
- Orchestrates audit job logic
- Depends on ports (DualWriteLedgerPort, MessagingPort, MetricsPort)
- No infrastructure dependencies
"""

import logging
from datetime import UTC, datetime
from typing import Any

from planning.application.dto.dual_write_operation import DualWriteOperation
from planning.application.ports.dual_write_ledger_port import DualWriteLedgerPort
from planning.application.ports.messaging_port import MessagingPort
from planning.application.ports.metrics_port import MetricsPort

logger = logging.getLogger(__name__)


class AuditPendingOperationsUseCase:
    """Use case for auditing pending dual write operations.

    Responsibilities:
    - List old PENDING operations (older than threshold)
    - Re-publish reconcile events for stuck operations
    - Record metrics (pending count, age, attempts)

    Following Hexagonal Architecture:
    - Pure business logic, no infrastructure dependencies
    - Depends on ports (not concrete adapters)
    - Orchestrates reconciliation retry flow
    """

    def __init__(
        self,
        dual_write_ledger: DualWriteLedgerPort,
        messaging: MessagingPort,
        metrics: MetricsPort | None = None,
        age_threshold_seconds: float = 300.0,  # 5 minutes default
    ) -> None:
        """Initialize audit use case with dependencies.

        Args:
            dual_write_ledger: Port for accessing dual write ledger
            messaging: Port for publishing reconcile events
            metrics: Port for recording metrics (optional)
            age_threshold_seconds: Minimum age in seconds for operations to audit (default: 5 minutes)
        """
        self._ledger = dual_write_ledger
        self._messaging = messaging
        self._metrics = metrics
        self._age_threshold = age_threshold_seconds

    async def execute(self) -> dict[str, Any]:
        """Execute audit of pending operations.

        Process:
        1. List all PENDING operations
        2. Calculate metrics (count, max age)
        3. Find old PENDING operations (older than threshold)
        4. Re-publish reconcile events for old operations
        5. Record metrics

        Returns:
            Dictionary with audit results:
            - total_pending: Total number of pending operations
            - old_pending: Number of old pending operations
            - republished: Number of reconcile events republished
            - max_age_seconds: Maximum age of pending operations in seconds
        """
        # 1. List all PENDING operations
        all_pending = await self._ledger.list_pending_operations(limit=1000)

        # Calculate metrics
        total_pending = len(all_pending)
        max_age_seconds = 0.0

        if all_pending:
            # Calculate maximum age
            now = datetime.now(UTC)
            for operation in all_pending:
                age_seconds = self._calculate_age(operation, now)
                max_age_seconds = max(max_age_seconds, age_seconds)

                # Record age metric
                if self._metrics:
                    self._metrics.record_pending_age(age_seconds)

        # Record pending count metric
        if self._metrics:
            self._metrics.record_pending_count(total_pending)

        # 2. Find old PENDING operations (older than threshold)
        old_pending = await self._ledger.list_old_pending_operations(
            age_seconds=self._age_threshold,
            limit=100,
        )

        # 3. Re-publish reconcile events for old operations
        republished = 0
        for operation in old_pending:
            try:
                # Try to extract operation_type and entity_id from operation_id
                # Format: SHA256({operation_type}:{entity_id})
                # We can't reverse SHA256, so we need a different approach
                # For now, we'll use a default operation_type and empty operation_data
                # The reconciliation service should handle missing operation_data

                # Re-publish reconcile event (operation_data will be empty, service must reconstruct)
                await self._messaging.publish_dualwrite_reconcile_requested(
                    operation_id=operation.operation_id,
                    operation_type="unknown",  # Will be handled by reconciliation service
                    operation_data={},  # Will be reconstructed from Valkey if needed
                )

                republished += 1

                # Increment reconcile attempts metric
                if self._metrics:
                    self._metrics.increment_reconcile_attempts()

                logger.info(
                    f"Re-published reconcile event for old operation: "
                    f"operation_id={operation.operation_id}, "
                    f"age_seconds={self._calculate_age(operation, datetime.now(UTC))}"
                )

            except Exception as e:
                logger.error(
                    f"Failed to re-publish reconcile event for operation "
                    f"{operation.operation_id}: {e}",
                    exc_info=True,
                )
                continue

        results = {
            "total_pending": total_pending,
            "old_pending": len(old_pending),
            "republished": republished,
            "max_age_seconds": max_age_seconds,
        }

        logger.info(
            f"Audit completed: total_pending={total_pending}, "
            f"old_pending={len(old_pending)}, republished={republished}, "
            f"max_age_seconds={max_age_seconds:.2f}"
        )

        return results

    def _calculate_age(self, operation: DualWriteOperation, now: datetime) -> float:
        """Calculate age of operation in seconds.

        Args:
            operation: DualWriteOperation entity
            now: Current datetime

        Returns:
            Age in seconds
        """
        try:
            created_at = datetime.fromisoformat(
                operation.created_at.replace("Z", "+00:00")
            )
            delta = now - created_at
            return delta.total_seconds()
        except (ValueError, AttributeError) as e:
            logger.warning(
                f"Invalid timestamp format for operation {operation.operation_id}: {e}"
            )
            return 0.0
