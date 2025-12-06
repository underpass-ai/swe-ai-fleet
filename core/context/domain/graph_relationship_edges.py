"""GraphRelationshipEdges domain entity - Collection of relationship edges."""

from dataclasses import dataclass

from core.context.domain.relationship_error import RelationshipError
from core.context.domain.value_objects.graph_relationship_edge import GraphRelationshipEdge


@dataclass(frozen=True)
class GraphRelationshipEdges:
    """Domain entity representing a collection of relationship edges.

    This entity encapsulates:
    - List of GraphRelationshipEdge instances
    - Validation (all relationships must connect valid nodes)
    - Query methods (get_for_node, get_outgoing, get_incoming, count)

    Domain Invariants:
    - edges cannot be None (but can be empty)
    - All relationships must connect nodes that exist in the provided valid_node_ids set

    This is a pure domain entity with NO serialization methods.
    Use GraphRelationshipEdgesMapper in infrastructure layer for conversions.
    """

    edges: list[GraphRelationshipEdge]

    def __post_init__(self) -> None:
        """Validate graph relationship edges (fail-fast).

        Raises:
            ValueError: If validation fails
        """
        if self.edges is None:
            raise ValueError("GraphRelationshipEdges edges cannot be None (use empty list [])")

    def validate_against_nodes(self, valid_node_ids: set[str]) -> None:
        """Validate that all relationships connect valid nodes.

        This method should be called after construction to ensure
        all relationships connect nodes that exist in the aggregate.

        Args:
            valid_node_ids: Set of valid node ID strings

        Raises:
            RelationshipError: If any relationship connects invalid nodes
        """
        for rel in self.edges:
            if not rel.connects_valid_nodes(valid_node_ids):
                raise RelationshipError(
                    relationship=rel,
                    valid_node_ids=valid_node_ids,
                )

    def get_for_node(self, node_id: str) -> list[GraphRelationshipEdge]:
        """Get all relationships involving a specific node.

        Args:
            node_id: Node identifier

        Returns:
            List of relationships where node_id is either from or to
        """
        return [
            rel
            for rel in self.edges
            if rel.from_node.has_id(node_id) or rel.to_node.has_id(node_id)
        ]

    def get_outgoing(self, node_id: str) -> list[GraphRelationshipEdge]:
        """Get relationships where node_id is the source.

        Args:
            node_id: Source node identifier

        Returns:
            List of outgoing relationships
        """
        return [rel for rel in self.edges if rel.from_node.has_id(node_id)]

    def get_incoming(self, node_id: str) -> list[GraphRelationshipEdge]:
        """Get relationships where node_id is the target.

        Args:
            node_id: Target node identifier

        Returns:
            List of incoming relationships
        """
        return [rel for rel in self.edges if rel.to_node.has_id(node_id)]

    def count(self) -> int:
        """Get number of relationships.

        Returns:
            Count of relationships
        """
        return len(self.edges)

    def __str__(self) -> str:
        """Return human-readable representation."""
        return f"GraphRelationshipEdges(count={len(self.edges)})"

