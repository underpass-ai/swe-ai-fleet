"""Execution statistics entity."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionStats:
    """Statistics about deliberation executions.

    Tracks metrics about Ray Executor service performance and usage.

    Attributes:
        total_deliberations: Total number of deliberations executed
        active_deliberations: Currently running deliberations
        completed_deliberations: Successfully completed deliberations
        failed_deliberations: Failed deliberations
        average_execution_time_ms: Average execution time in milliseconds
    """

    total_deliberations: int
    active_deliberations: int
    completed_deliberations: int
    failed_deliberations: int
    average_execution_time_ms: float

    def __post_init__(self) -> None:
        """Validate execution stats invariants."""
        if self.total_deliberations < 0:
            raise ValueError("total_deliberations cannot be negative")

        if self.active_deliberations < 0:
            raise ValueError("active_deliberations cannot be negative")

        if self.completed_deliberations < 0:
            raise ValueError("completed_deliberations cannot be negative")

        if self.failed_deliberations < 0:
            raise ValueError("failed_deliberations cannot be negative")

        if self.average_execution_time_ms < 0:
            raise ValueError("average_execution_time_ms cannot be negative")

