"""Metrics port for ceremony engine (step/publish counters).

Following Hexagonal Architecture:
- This is a PORT (interface) in the application layer
- Infrastructure adapters implement this port (Prometheus, etc.)
- Application depends on PORT, not concrete implementation
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class CeremonyMetricsPort(Protocol):
    """Port for ceremony execution metrics.

    Provides counters for:
    - Step success/failure
    - Publish success/failure (step.executed, transition.applied)

    Following Hexagonal Architecture:
    - This is a PORT (interface)
    - Infrastructure provides ADAPTERS (Prometheus, no-op, etc.)
    - Application depends on PORT, not concrete implementation
    """

    def increment_step_success(self) -> None:
        """Increment step execution success counter."""
        ...

    def increment_step_failure(self) -> None:
        """Increment step execution failure counter."""
        ...

    def increment_publish_success(self) -> None:
        """Increment publish success counter (step.executed or transition.applied)."""
        ...

    def increment_publish_failure(self) -> None:
        """Increment publish failure counter."""
        ...
