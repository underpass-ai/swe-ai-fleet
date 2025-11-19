"""Duration value object for task effort estimation."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Duration:
    """
    Value Object: Task duration in hours.

    Domain Invariants:
    - Duration must be >= 0 (0 means not estimated)
    - Duration has maximum value (reasonable limit)
    - Immutable (frozen=True)

    Business Rules:
    - Duration represents estimated effort in hours
    - 0 means not estimated yet
    - Maximum reasonable duration is 1000 hours (~6 months full-time)
    """

    hours: int

    def __post_init__(self) -> None:
        """
        Fail-fast validation.

        Raises:
            ValueError: If duration is invalid.
        """
        if self.hours < 0:
            raise ValueError("Duration hours cannot be negative")

        if self.hours > 1000:
            raise ValueError(f"Duration too large (max 1000 hours): {self.hours}")

    def __str__(self) -> str:
        """String representation for logging."""
        return f"{self.hours}h"

    def to_hours(self) -> int:
        """Get duration in hours (primitive extraction).

        Returns:
            Hours as integer
        """
        return self.hours

    @classmethod
    def zero(cls) -> "Duration":
        """Factory: Create zero duration (not estimated).

        Returns:
            Duration with 0 hours
        """
        return cls(0)

    @classmethod
    def from_optional(cls, hours: int | None) -> "Duration":
        """Factory: Create Duration from optional value (handles defaults).

        Tell, Don't Ask: Duration knows how to handle optional values.

        Args:
            hours: Hours value (None or <= 0 defaults to 0)

        Returns:
            Duration value object
        """
        if hours is None or hours <= 0:
            return cls.zero()
        return cls(hours)

