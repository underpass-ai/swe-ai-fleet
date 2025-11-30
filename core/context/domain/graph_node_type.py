"""GraphNodeType Enum - Types of nodes in the Neo4j graph."""

from enum import Enum


class GraphNodeType(str, Enum):
    """Types of nodes that can appear in the Neo4j graph.

    This enum represents all valid node types that can be queried
    or appear as neighbors in graph relationship queries.

    Used for:
    - Validating node types in queries
    - Determining node type from Neo4j labels
    - Type-safe node type handling in domain logic
    """

    PROJECT = "Project"
    EPIC = "Epic"
    STORY = "Story"
    TASK = "Task"
    PLAN_VERSION = "PlanVersion"
    DECISION = "Decision"
    USER = "User"

    @classmethod
    def from_label(cls, label: str) -> "GraphNodeType | None":
        """Get GraphNodeType from a Neo4j label string.

        Args:
            label: Neo4j label string

        Returns:
            GraphNodeType if label matches, None otherwise
        """
        try:
            return cls(label)
        except ValueError:
            return None

    @classmethod
    def is_valid_label(cls, label: str) -> bool:
        """Check if a label string is a valid GraphNodeType.

        Args:
            label: Neo4j label string

        Returns:
            True if label is a valid GraphNodeType, False otherwise
        """
        return cls.from_label(label) is not None

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

