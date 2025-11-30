"""GraphRelationshipsResult Value Object - Result containing a node and its graph relationships."""

from dataclasses import dataclass

from core.context.domain.value_objects.graph_node import GraphNode
from core.context.domain.value_objects.graph_relationship_edge import GraphRelationshipEdge


@dataclass(frozen=True)
class GraphRelationshipsResult:
    """Value Object containing a graph node and its relationships.

    This Value Object encapsulates the result of a graph relationship query,
    including the requested node, its neighbor nodes, and the relationships
    connecting them.

    Domain Invariants:
    - node cannot be None
    - neighbors and relationships lists cannot be None (but can be empty)

    This is a pure domain Value Object with NO serialization methods.
    Use GraphRelationshipsResultMapper in infrastructure layer for conversions.
    """

    node: GraphNode
    neighbors: list[GraphNode]
    relationships: list[GraphRelationshipEdge]

    def __post_init__(self) -> None:
        """Validate graph relationships result (fail-fast).

        Raises:
            ValueError: If validation fails
        """
        if self.node is None:
            raise ValueError("GraphRelationshipsResult node cannot be None")

        # Validate lists are not None (fail-fast, no mutation)
        if self.neighbors is None:
            raise ValueError("GraphRelationshipsResult neighbors cannot be None (use empty list [])")
        if self.relationships is None:
            raise ValueError("GraphRelationshipsResult relationships cannot be None (use empty list [])")

    def __str__(self) -> str:
        """Return human-readable representation."""
        return (
            f"GraphRelationshipsResult(node={self.node.id}, "
            f"neighbors={len(self.neighbors)}, relationships={len(self.relationships)})"
        )

