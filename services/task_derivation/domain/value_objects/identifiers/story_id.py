"""Story ID value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StoryId:
    """
    Value Object: Unique identifier for a Story.

    Domain Invariants:
    - Story ID cannot be empty
    - Story ID must follow format: s-{uuid} or custom format

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

        # Optional: validate format (e.g., s-{uuid})
        # if not self.value.startswith("s-"):
        #     raise ValueError(f"StoryId must start with 's-': {self.value}")

    def __str__(self) -> str:
        """String representation for logging."""
        return self.value

