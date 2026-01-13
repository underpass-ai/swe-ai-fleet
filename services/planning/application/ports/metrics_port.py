"""Metrics port for dual write operations.

Following Hexagonal Architecture:
- This is a PORT (interface) in the application layer
- Infrastructure adapters implement this port (Prometheus, etc.)
- Application depends on PORT, not concrete implementation
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class MetricsPort(Protocol):
    """Port for dual write metrics operations.

    Provides metrics for monitoring dual write operations:
    - Pending operations count
    - Pending operations age (maximum age in seconds)
    - Reconciliation attempts (total counter)

    Following Hexagonal Architecture:
    - This is a PORT (interface)
    - Infrastructure provides ADAPTERS (PrometheusMetricsAdapter, etc.)
    - Application depends on PORT, not concrete implementation
    """

    def record_pending_count(self, count: int) -> None:
        """Record the current number of pending operations.

        Args:
            count: Number of pending operations

        Raises:
            ValueError: If count is negative
        """
        ...

    def record_pending_age(self, age_seconds: float) -> None:
        """Record the age of a pending operation.

        Args:
            age_seconds: Age of pending operation in seconds

        Raises:
            ValueError: If age_seconds is negative
        """
        ...

    def increment_reconcile_attempts(self) -> None:
        """Increment the total number of reconciliation attempts."""
        ...
