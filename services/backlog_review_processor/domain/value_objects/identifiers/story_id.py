"""Story ID value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StoryId:
    """
    Value Object: Unique identifier for a Story.

    Domain Invariants:
    - Story ID cannot be empty

    Immutability: frozen=True ensures no mutation after creation.
    """

    value: str

    def __post_init__(self) -> None:
        """
        Fail-fast validation.

        Raises:
            ValueError: If story ID is empty or invalid format.
        """
        if not self.value:
            raise ValueError("StoryId cannot be empty")

        if not self.value.strip():
            raise ValueError("StoryId cannot be whitespace")

    def __str__(self) -> str:
        """String representation for logging."""
        return self.value

