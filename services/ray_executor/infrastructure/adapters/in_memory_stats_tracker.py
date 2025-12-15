from __future__ import annotations

from typing import Any

from services.ray_executor.domain.ports import StatsTrackerPort


class InMemoryStatsTrackerAdapter(StatsTrackerPort):
    """In-memory implementation of StatsTrackerPort.

    This adapter is responsible for tracking execution statistics for the
    Ray Executor service using a shared mutable dictionary.
    """

    def __init__(self, stats: dict[str, Any]) -> None:
        self._stats = stats

    def record_completed(self, execution_time_seconds: float) -> None:
        self._stats.setdefault("execution_times", []).append(execution_time_seconds)
        self._stats["completed_deliberations"] = (
            self._stats.get("completed_deliberations", 0) + 1
        )

    def record_failed(self) -> None:
        self._stats["failed_deliberations"] = (
            self._stats.get("failed_deliberations", 0) + 1
        )

    def increment_active(self) -> None:
        self._stats["active_deliberations"] = (
            self._stats.get("active_deliberations", 0) + 1
        )
        self._stats["total_deliberations"] = (
            self._stats.get("total_deliberations", 0) + 1
        )

    def decrement_active(self) -> None:
        self._stats["active_deliberations"] = max(
            0,
            self._stats.get("active_deliberations", 0) - 1,
        )

