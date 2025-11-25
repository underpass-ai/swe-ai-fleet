"""TaskId value object for Planning Service."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskId:
    """Value Object for Task identifier.

    Domain Invariant: TaskId cannot be empty.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate TaskId (fail-fast).

        Raises:
            ValueError: If task ID is empty or whitespace
        """
        if not self.value or not self.value.strip():
            raise ValueError("TaskId cannot be empty")

    def __str__(self) -> str:
        """String representation.

        Returns:
            String value
        """
        return self.value

