"""GraphRelationshipEdgeProperties Value Object - Properties of a graph relationship edge."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GraphRelationshipEdgeProperties:
    """Value Object representing properties of a graph relationship edge.

    This Value Object encapsulates the properties/metadata associated with
    a relationship in the Neo4j graph database.

    Domain Invariants:
    - properties dict cannot be None (but can be empty)

    This is a pure domain Value Object with NO serialization methods.
    Use GraphRelationshipEdgePropertiesMapper in infrastructure layer for conversions.
    """

    properties: dict[str, Any]

    def __post_init__(self) -> None:
        """Validate graph relationship edge properties (fail-fast).

        Raises:
            ValueError: If validation fails
        """
        if self.properties is None:
            raise ValueError(
                "GraphRelationshipEdgeProperties properties cannot be None (use empty dict {})"
            )

    def get(self, key: str, default: Any = None) -> Any:
        """Get property value by key.

        Args:
            key: Property key
            default: Default value if key not found

        Returns:
            Property value or default
        """
        return self.properties.get(key, default)

    def has(self, key: str) -> bool:
        """Check if property exists.

        Args:
            key: Property key

        Returns:
            True if property exists
        """
        return key in self.properties

    def __str__(self) -> str:
        """Return human-readable representation."""
        return f"GraphRelationshipEdgeProperties({len(self.properties)} properties)"

