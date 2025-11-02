"""UserName value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class UserName:
    """
    Value Object: User identifier or name.

    Domain Invariants:
    - UserName must not be empty
    - UserName has maximum length (100 chars)
    - Immutable (frozen=True)

    Business Rules:
    - Represents who performed an action (created_by, approved_by, etc.)
    - Should be a valid user identifier from IAM/auth system
    """

    value: str

    def __post_init__(self) -> None:
        """
        Fail-fast validation.

        Raises:
            ValueError: If username is invalid.
        """
        if not self.value or not self.value.strip():
            raise ValueError("UserName cannot be empty")

        if len(self.value) > 100:
            raise ValueError(f"UserName too long (max 100 chars): {len(self.value)}")

    def __str__(self) -> str:
        """String representation for logging."""
        return self.value

