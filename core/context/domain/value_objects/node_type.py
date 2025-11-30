"""NodeType Value Object - Type of a graph node."""

from dataclasses import dataclass


@dataclass(frozen=True)
class NodeType:
    """Value Object for graph node type.

    This Value Object encapsulates a node type from the Neo4j graph,
    preventing primitive obsession and ensuring validation.

    Domain Invariants:
    - value must be a valid node type (Project, Epic, Story, Task, etc.)

    This is a pure domain Value Object with NO serialization methods.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate node type (fail-fast).

        Raises:
            ValueError: If validation fails
        """
        if not self.value or not self.value.strip():
            raise ValueError("NodeType value cannot be empty")

        valid_types = {
            "Project",
            "Epic",
            "Story",
            "Task",
            "PlanVersion",
            "Decision",
            "User",
            "Unknown",
        }
        if self.value not in valid_types:
            raise ValueError(
                f"Invalid node type: {self.value}. "
                f"Must be one of: {', '.join(sorted(valid_types))}"
            )

    def to_string(self) -> str:
        """Convert to string representation.

        Explicit method following Tell, Don't Ask principle.

        Returns:
            String representation of node type
        """
        return self.value

    def __str__(self) -> str:
        """String representation for compatibility."""
        return self.to_string()

