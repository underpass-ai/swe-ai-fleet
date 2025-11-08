"""StoryConstraints value object."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StoryConstraints:
    """Value Object for story constraints.

    Constraints define technical or business limitations for story implementation.
    Examples: max_response_time_ms, max_database_queries, required_frameworks, etc.

    Note: This is a transitional design. As constraints are better understood,
    we should evolve this into specific constraint types (TimeConstraint, ResourceConstraint, etc.).
    """

    constraints: dict[str, Any]  # Temporary dict until we identify common patterns

    def __post_init__(self) -> None:
        """Validate constraints."""
        if not isinstance(self.constraints, dict):
            raise ValueError("Constraints must be a dictionary")

    @staticmethod
    def empty() -> "StoryConstraints":
        """Create empty constraints.

        Returns:
            Empty StoryConstraints value object
        """
        return StoryConstraints(constraints={})

    @staticmethod
    def from_dict(constraints_dict: dict[str, Any]) -> "StoryConstraints":
        """Create StoryConstraints from dictionary.

        Args:
            constraints_dict: Dictionary of constraints

        Returns:
            StoryConstraints value object
        """
        return StoryConstraints(constraints=dict(constraints_dict))  # Defensive copy

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary of constraints
        """
        return dict(self.constraints)  # Defensive copy

    def get(self, key: str, default: Any = None) -> Any:
        """Get constraint value.

        Args:
            key: Constraint key
            default: Default value if key not found

        Returns:
            Constraint value or default
        """
        return self.constraints.get(key, default)

    def has(self, key: str) -> bool:
        """Check if constraint exists.

        Args:
            key: Constraint key

        Returns:
            True if constraint exists
        """
        return key in self.constraints






