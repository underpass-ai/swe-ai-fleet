"""Title value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Title:
    """
    Value Object: Story title.

    Domain Invariants:
    - Title must not be empty
    - Title has maximum length (200 chars)
    - Immutable (frozen=True)

    Business Rules:
    - Titles should be concise user stories
    - Should follow "As a... I want... So that..." format (not enforced here)
    """

    value: str

    def __post_init__(self) -> None:
        """
        Fail-fast validation.

        Raises:
            ValueError: If title is invalid.
        """
        if not self.value or not self.value.strip():
            raise ValueError("Title cannot be empty")

        if len(self.value) > 200:
            raise ValueError(f"Title too long (max 200 chars): {len(self.value)}")

    def __str__(self) -> str:
        """String representation for logging."""
        return self.value

