"""Get execution statistics use case."""

import logging
import time

from services.ray_executor.domain.entities import ExecutionStats

logger = logging.getLogger(__name__)


class GetStatsUseCase:
    """Use case for retrieving execution statistics.

    This use case calculates and returns statistics about the Ray Executor
    service performance and usage.

    Responsibilities:
    - Calculate average execution time
    - Return statistics as domain entity

    Following Hexagonal Architecture:
    - Pure business logic, no infrastructure dependencies
    - Returns domain entity (ExecutionStats)
    """

    def __init__(
        self,
        stats_tracker: dict,
        start_time: float,
    ):
        """Initialize use case with dependencies.

        Args:
            stats_tracker: Shared statistics dictionary
            start_time: Service start time (unix timestamp)
        """
        self._stats = stats_tracker
        self._start_time = start_time

    async def execute(self) -> tuple[ExecutionStats, int]:
        """Execute the statistics retrieval use case.

        Returns:
            Tuple of (ExecutionStats entity, uptime_seconds)
        """
        # Calculate uptime
        uptime_seconds = int(time.time() - self._start_time)

        # Calculate average execution time
        avg_time_ms = 0.0
        if self._stats['execution_times']:
            avg_time_sec = sum(self._stats['execution_times']) / len(self._stats['execution_times'])
            avg_time_ms = avg_time_sec * 1000  # Convert to milliseconds

        # Build domain entity
        stats = ExecutionStats(
            total_deliberations=self._stats['total_deliberations'],
            active_deliberations=self._stats['active_deliberations'],
            completed_deliberations=self._stats['completed_deliberations'],
            failed_deliberations=self._stats['failed_deliberations'],
            average_execution_time_ms=avg_time_ms,
        )

        return stats, uptime_seconds

