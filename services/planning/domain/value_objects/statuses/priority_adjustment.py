"""PriorityAdjustment - Enum for PO priority adjustment values.

Domain Layer (Enum):
- Encapsulates valid priority adjustment values
- Used when PO overrides plan preliminary priority
- Type-safe enum instead of string literals
"""

from dataclasses import dataclass
from enum import Enum


class PriorityAdjustmentEnum(str, Enum):
    """
    Enum for priority adjustment values.

    When a PO approves a plan, they can optionally adjust the priority
    from the plan preliminary. This enum defines the valid values.

    Values:
    - HIGH: Increase priority (urgent/important)
    - MEDIUM: Keep medium priority (standard)
    - LOW: Decrease priority (can wait)
    """

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

    def __str__(self) -> str:
        """String representation.

        Returns:
            The enum value as string
        """
        return self.value


@dataclass(frozen=True)
class PriorityAdjustment:
    """
    Value object wrapping PriorityAdjustmentEnum.

    This provides a domain concept for priority adjustments with
    validation and type safety.

    Following DDD:
    - Immutable value object (@dataclass(frozen=True))
    - Wraps enum for type safety
    - Self-documenting domain concept
    """

    value: PriorityAdjustmentEnum

    def __str__(self) -> str:
        """String representation.

        Returns:
            The enum value as string
        """
        return self.value.value

    def __repr__(self) -> str:
        """Developer representation.

        Returns:
            Developer-friendly string representation
        """
        return f"PriorityAdjustment(value={self.value.value})"

    @classmethod
    def from_string(cls, value: str) -> "PriorityAdjustment":
        """
        Create PriorityAdjustment from string.

        Args:
            value: String value (HIGH, MEDIUM, or LOW)

        Returns:
            PriorityAdjustment instance

        Raises:
            ValueError: If value is not a valid priority adjustment
        """
        try:
            enum_value = PriorityAdjustmentEnum(value.strip().upper())
            return cls(value=enum_value)
        except ValueError:
            valid_values = [e.value for e in PriorityAdjustmentEnum]
            raise ValueError(
                f"Invalid priority adjustment: '{value}'. "
                f"Must be one of: {', '.join(sorted(valid_values))}"
            )

