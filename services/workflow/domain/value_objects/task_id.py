"""Task identifier value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskId:
    """Task identifier value object.

    Represents a unique task identifier in the workflow.
    Immutable following DDD principles.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate business invariants (fail-fast).

        Type validation is handled by type hints.
        """
        if not self.value:
            raise ValueError("TaskId cannot be empty")

    def __str__(self) -> str:
        """String representation."""
        return self.value

