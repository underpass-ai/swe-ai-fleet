"""Priority value object for task ordering."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Priority:
    """
    Value Object: Task priority.

    Domain Invariants:
    - Priority must be >= 1 (1 = highest priority)
    - Priority has maximum value (reasonable limit)
    - Immutable (frozen=True)

    Business Rules:
    - Lower number = higher priority (1 is highest)
    - Used for task ordering and execution sequence
    - Maximum reasonable priority is 1000
    """

    value: int

    def __post_init__(self) -> None:
        """
        Fail-fast validation.

        Raises:
            ValueError: If priority is invalid.
        """
        if self.value < 1:
            raise ValueError("Priority must be >= 1 (1 = highest priority)")

        if self.value > 1000:
            raise ValueError(f"Priority too large (max 1000): {self.value}")

    def __str__(self) -> str:
        """String representation for logging."""
        return str(self.value)

    def to_int(self) -> int:
        """Get priority as integer (primitive extraction).

        Returns:
            Priority as integer
        """
        return self.value

    def is_higher_than(self, other: "Priority") -> bool:
        """Check if this priority is higher than other.

        Args:
            other: Priority to compare

        Returns:
            True if this priority is higher (lower number)
        """
        return self.value < other.value

    @classmethod
    def highest(cls) -> "Priority":
        """Factory: Create highest priority (1).

        Returns:
            Priority with value 1
        """
        return cls(1)

    @classmethod
    def from_optional(cls, value: int | None) -> "Priority":
        """Factory: Create Priority from optional value (handles defaults).

        Tell, Don't Ask: Priority knows how to handle optional values.
        Fail Fast: Invalid values (< 1) will fail in __post_init__.

        Args:
            value: Priority value (None or 0 defaults to 1, < 1 fails fast)

        Returns:
            Priority value object

        Raises:
            ValueError: If value is < 1 (fail fast)
        """
        if value is None or value == 0:
            return cls.highest()
        # Pass value directly - __post_init__ will validate and fail fast if invalid
        return cls(value)

