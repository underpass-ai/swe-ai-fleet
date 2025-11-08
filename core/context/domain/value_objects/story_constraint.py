"""StoryConstraint Value Object - Single constraint on a story."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StoryConstraint:
    """A single constraint that limits or guides story implementation.

    Constraints define boundaries and restrictions that must be respected
    during development (e.g., "Must use Neo4j", "Response time < 100ms").

    This is a Value Object - immutable and replaceable.
    """

    constraint_type: str  # "technical", "performance", "security", "business", etc.
    description: str
    priority: str = "medium"  # "low", "medium", "high", "critical"

    def __post_init__(self) -> None:
        """Validate constraint."""
        if not self.constraint_type or not self.constraint_type.strip():
            raise ValueError("Constraint type cannot be empty")
        if not self.description or not self.description.strip():
            raise ValueError("Constraint description cannot be empty")

        valid_priorities = {"low", "medium", "high", "critical"}
        if self.priority not in valid_priorities:
            raise ValueError(
                f"Invalid priority '{self.priority}'. "
                f"Must be one of: {', '.join(sorted(valid_priorities))}"
            )

    def is_critical(self) -> bool:
        """Check if this is a critical constraint.

        Returns:
            True if priority is critical
        """
        return self.priority == "critical"

    def is_high_priority(self) -> bool:
        """Check if this is high or critical priority.

        Returns:
            True if priority is high or critical
        """
        return self.priority in {"high", "critical"}

    def __str__(self) -> str:
        """Return human-readable representation."""
        return f"[{self.constraint_type.upper()}] {self.description} (priority: {self.priority})"

