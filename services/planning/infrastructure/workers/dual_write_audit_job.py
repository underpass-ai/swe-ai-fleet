"""Worker for auditing pending dual write operations.

Following Hexagonal Architecture:
- Infrastructure layer worker
- Executes AuditPendingOperationsUseCase periodically
- Background task that runs in a loop
"""

import asyncio
import logging

from planning.application.usecases.audit_pending_operations_usecase import (
    AuditPendingOperationsUseCase,
)

logger = logging.getLogger(__name__)


class DualWriteAuditJob:
    """Worker for auditing pending dual write operations.

    Responsibilities:
    - Execute audit use case periodically
    - Run in background loop
    - Handle errors gracefully

    Following Hexagonal Architecture:
    - Infrastructure worker (runs periodically)
    - Delegates to application use case
    - No business logic, only orchestration
    """

    def __init__(
        self,
        audit_use_case: AuditPendingOperationsUseCase,
        interval_seconds: float = 60.0,  # 1 minute default
    ) -> None:
        """Initialize audit job with dependencies.

        Args:
            audit_use_case: Use case for auditing pending operations
            interval_seconds: Interval between audit runs in seconds (default: 60 seconds)
        """
        self._use_case = audit_use_case
        self._interval = interval_seconds
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start audit job background task."""
        if self._task and not self._task.done():
            logger.warning("Audit job already running")
            return

        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"DualWriteAuditJob started (interval={self._interval}s)")

        # Yield to event loop to ensure task is scheduled
        await asyncio.sleep(0)

    async def _run_loop(self) -> None:
        """Main loop that runs audit periodically."""
        logger.info("🔄 DualWriteAuditJob: loop started")

        while True:
            try:
                # Execute audit use case
                results = await self._use_case.execute()

                # Format max_age_seconds safely
                try:
                    max_age = float(results.get("max_age_seconds", 0.0))
                    max_age_str = f"{max_age:.2f}"
                except (ValueError, TypeError):
                    max_age_str = str(results.get("max_age_seconds", 0.0))

                logger.debug(
                    f"Audit job completed: total_pending={results.get('total_pending', 0)}, "
                    f"old_pending={results.get('old_pending', 0)}, "
                    f"republished={results.get('republished', 0)}, "
                    f"max_age_seconds={max_age_str}"
                )

                # Wait for next interval
                await asyncio.sleep(self._interval)

            except asyncio.CancelledError:
                logger.info("DualWriteAuditJob loop cancelled")
                raise  # Re-raise CancelledError to properly propagate cancellation

            except Exception as e:
                logger.error(f"Error in audit job: {e}", exc_info=True)
                # Continue loop even on error (don't crash)
                await asyncio.sleep(self._interval)

    async def stop(self) -> None:
        """Stop audit job and cleanup resources."""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                # CancelledError is expected when cancelling a task
                logger.info("DualWriteAuditJob stopped")
                raise  # Re-raise CancelledError after cleanup (linter requirement)

        logger.info("DualWriteAuditJob stopped")
