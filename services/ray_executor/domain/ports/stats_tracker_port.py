"""Port for tracking execution statistics."""

from __future__ import annotations

from typing import Protocol


class StatsTrackerPort(Protocol):
    """Port defining the interface for execution statistics tracking.

    This port abstracts how statistics about deliberations are stored and updated,
    so application/use case logic does not depend on a concrete in-memory dict.
    """

    def record_completed(self, execution_time_seconds: float) -> None:
        """Record a successfully completed deliberation.

        Args:
            execution_time_seconds: Execution time in seconds for the deliberation.
        """
        ...

    def record_failed(self) -> None:
        """Record a failed deliberation."""
        ...

    def increment_active(self) -> None:
        """Increment the number of active deliberations."""
        ...

    def decrement_active(self) -> None:
        """Decrement the number of active deliberations."""
        ...

