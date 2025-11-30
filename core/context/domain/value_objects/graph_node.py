"""GraphNode Value Object - Represents a node in the Neo4j graph for visualization."""

from dataclasses import dataclass

from core.context.domain.value_objects.node_id import NodeId
from core.context.domain.value_objects.node_label import NodeLabel
from core.context.domain.value_objects.node_properties import NodeProperties
from core.context.domain.value_objects.node_title import NodeTitle
from core.context.domain.value_objects.node_type import NodeType


@dataclass(frozen=True)
class GraphNode:
    """Value Object representing a graph node for visualization.

    This Value Object encapsulates a node from the Neo4j graph database,
    using domain Value Objects instead of primitive strings.

    Domain Invariants:
    - id cannot be None
    - labels cannot be None (but can be empty)
    - properties cannot be None
    - node_type cannot be None
    - title cannot be None

    This is a pure domain Value Object with NO serialization methods.
    Use GraphNodeMapper in infrastructure layer for conversions.
    """

    id: NodeId
    labels: list[NodeLabel]
    properties: NodeProperties
    node_type: NodeType
    title: NodeTitle

    def __post_init__(self) -> None:
        """Validate graph node (fail-fast).

        Raises:
            ValueError: If validation fails
        """
        if self.id is None:
            raise ValueError("GraphNode id cannot be None")

        if self.labels is None:
            raise ValueError("GraphNode labels cannot be None (use empty list [])")

        if self.properties is None:
            raise ValueError("GraphNode properties cannot be None")

        if self.node_type is None:
            raise ValueError("GraphNode node_type cannot be None")

        if self.title is None:
            raise ValueError("GraphNode title cannot be None")

    def get_id_string(self) -> str:
        """Get node ID as string.

        Explicit method following Tell, Don't Ask principle.

        Returns:
            String representation of node ID
        """
        return self.id.to_string()

    def has_id(self, node_id: str) -> bool:
        """Check if this node has the given ID.

        Args:
            node_id: Node identifier to check

        Returns:
            True if this node's ID matches
        """
        return self.id.value == node_id

    def __str__(self) -> str:
        """Return human-readable representation."""
        return (
            f"GraphNode(id={self.id.value}, type={self.node_type.value}, "
            f"title={self.title.value})"
        )

