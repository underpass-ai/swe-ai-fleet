"""NodeTitle Value Object - Title of a graph node."""

from dataclasses import dataclass


@dataclass(frozen=True)
class NodeTitle:
    """Value Object for graph node title.

    This Value Object encapsulates a node title from the Neo4j graph,
    preventing primitive obsession and ensuring validation.

    Domain Invariants:
    - value cannot be empty

    This is a pure domain Value Object with NO serialization methods.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate node title (fail-fast).

        Raises:
            ValueError: If validation fails
        """
        if not self.value or not self.value.strip():
            raise ValueError("NodeTitle value cannot be empty")

    def to_string(self) -> str:
        """Convert to string representation.

        Explicit method following Tell, Don't Ask principle.

        Returns:
            String representation of node title
        """
        return self.value

    def __str__(self) -> str:
        """String representation for compatibility."""
        return self.to_string()

