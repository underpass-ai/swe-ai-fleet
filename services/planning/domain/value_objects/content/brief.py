"""Brief value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Brief:
    """
    Value Object: Story brief description.

    Domain Invariants:
    - Brief must not be empty
    - Brief has maximum length (2000 chars)
    - Immutable (frozen=True)

    Business Rules:
    - Brief provides context for story
    - Should include acceptance criteria
    - Should be detailed enough for DoR evaluation
    """

    value: str

    def __post_init__(self) -> None:
        """
        Fail-fast validation.

        Raises:
            ValueError: If brief is invalid.
        """
        if not self.value or not self.value.strip():
            raise ValueError("Brief cannot be empty")

        if len(self.value) > 2000:
            raise ValueError(f"Brief too long (max 2000 chars): {len(self.value)}")

    def __str__(self) -> str:
        """String representation for logging."""
        return self.value[:100] + "..." if len(self.value) > 100 else self.value

