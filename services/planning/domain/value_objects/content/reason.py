"""Reason value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Reason:
    """
    Value Object: Rejection or transition reason.

    Domain Invariants:
    - Reason must not be empty
    - Reason has maximum length (500 chars)
    - Immutable (frozen=True)

    Business Rules:
    - Reasons must be actionable
    - Should explain why decision was rejected or why transition occurred
    - Used for learning and improvement
    """

    value: str

    def __post_init__(self) -> None:
        """
        Fail-fast validation.

        Raises:
            ValueError: If reason is invalid.
        """
        if not self.value or not self.value.strip():
            raise ValueError("Reason cannot be empty")

        if len(self.value) > 500:
            raise ValueError(f"Reason too long (max 500 chars): {len(self.value)}")

    def __str__(self) -> str:
        """String representation for logging."""
        return self.value

