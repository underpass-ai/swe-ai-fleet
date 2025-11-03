"""Comment value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Comment:
    """
    Value Object: Optional comment or note.

    Domain Invariants:
    - Comment can be empty (optional)
    - Comment has maximum length (1000 chars)
    - Immutable (frozen=True)

    Business Rules:
    - Comments provide additional context
    - Used for approvals, transitions, decisions
    """

    value: str

    def __post_init__(self) -> None:
        """
        Fail-fast validation.

        Raises:
            ValueError: If comment is invalid.
        """
        if len(self.value) > 1000:
            raise ValueError(f"Comment too long (max 1000 chars): {len(self.value)}")

    def is_empty(self) -> bool:
        """Check if comment is empty."""
        return not self.value or not self.value.strip()

    def __str__(self) -> str:
        """String representation for logging."""
        return self.value if self.value else "(no comment)"

