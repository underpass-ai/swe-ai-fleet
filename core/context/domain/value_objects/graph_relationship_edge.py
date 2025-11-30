"""GraphRelationshipEdge Value Object - Represents a relationship edge in the Neo4j graph for visualization."""

from dataclasses import dataclass

from core.context.domain.graph_relation_type import GraphRelationType
from core.context.domain.value_objects.graph_node import GraphNode
from core.context.domain.value_objects.graph_relationship_edge_properties import (
    GraphRelationshipEdgeProperties,
)


@dataclass(frozen=True)
class GraphRelationshipEdge:
    """Value Object representing a relationship edge between two graph nodes.

    This Value Object encapsulates a relationship from the Neo4j graph database,
    using domain entities (GraphNode) instead of primitive strings.

    Domain Invariants:
    - from_node cannot be None
    - to_node cannot be None
    - relationship_type cannot be None
    - properties cannot be None

    This is a pure domain Value Object with NO serialization methods.
    Use GraphRelationshipEdgeMapper in infrastructure layer for conversions.
    """

    from_node: GraphNode
    to_node: GraphNode
    relationship_type: GraphRelationType
    properties: GraphRelationshipEdgeProperties

    def __post_init__(self) -> None:
        """Validate graph relationship edge (fail-fast).

        Raises:
            ValueError: If validation fails
        """
        if self.from_node is None:
            raise ValueError("GraphRelationshipEdge from_node cannot be None")

        if self.to_node is None:
            raise ValueError("GraphRelationshipEdge to_node cannot be None")

        if self.relationship_type is None:
            raise ValueError("GraphRelationshipEdge relationship_type cannot be None")

        if self.properties is None:
            raise ValueError("GraphRelationshipEdge properties cannot be None")

    def connects_valid_nodes(self, valid_node_ids: set[str]) -> bool:
        """Check if this relationship connects nodes with valid IDs.

        Args:
            valid_node_ids: Set of valid node ID strings

        Returns:
            True if both from_node and to_node have IDs in the valid set
        """
        return (
            self.from_node.get_id_string() in valid_node_ids
            and self.to_node.get_id_string() in valid_node_ids
        )

    def __str__(self) -> str:
        """Return human-readable representation."""
        return (
            f"GraphRelationshipEdge(from={self.from_node.get_id_string()}, "
            f"to={self.to_node.get_id_string()}, type={self.relationship_type.value})"
        )

