"""NodeProperties Value Object - Properties of a graph node."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NodeProperties:
    """Value Object representing properties of a graph node.

    This Value Object encapsulates the properties/metadata associated with
    a node in the Neo4j graph database.

    Domain Invariants:
    - properties dict cannot be None (but can be empty)

    This is a pure domain Value Object with NO serialization methods.
    Use NodePropertiesMapper in infrastructure layer for conversions.
    """

    properties: dict[str, Any]

    def __post_init__(self) -> None:
        """Validate node properties (fail-fast).

        Raises:
            ValueError: If validation fails
        """
        if self.properties is None:
            raise ValueError(
                "NodeProperties properties cannot be None (use empty dict {})"
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
        return f"NodeProperties({len(self.properties)} properties)"

