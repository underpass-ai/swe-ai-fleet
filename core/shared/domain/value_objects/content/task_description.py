"""TaskDescription value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskDescription:
    """
    Value Object: Task description.

    Domain Invariants:
    - TaskDescription must not be empty
    - TaskDescription has maximum length (2000 chars)
    - Immutable (frozen=True)

    Business Rules:
    - TaskDescription provides context for task execution
    - Should include implementation details
    - Should be detailed enough for task execution
    """

    value: str

    def __post_init__(self) -> None:
        """
        Fail-fast validation.

        Raises:
            ValueError: If task description is invalid.
        """
        if not self.value or not self.value.strip():
            raise ValueError("TaskDescription cannot be empty")

        if len(self.value) > 2000:
            raise ValueError(f"TaskDescription too long (max 2000 chars): {len(self.value)}")

    def __str__(self) -> str:
        """String representation for logging."""
        return self.value[:100] + "..." if len(self.value) > 100 else self.value

