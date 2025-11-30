"""GraphRelationships Aggregate Root - Encapsulates a node and its graph relationships.

This Aggregate Root represents a node in the Neo4j graph along with its
neighbor nodes and the relationships connecting them.
"""

from dataclasses import dataclass
from typing import Any

from core.context.domain.graph_neighbors import GraphNeighbors
from core.context.domain.graph_relationship_edges import GraphRelationshipEdges
from core.context.domain.services.graph_relationships_builder import (
    GraphRelationshipsBuilder,
)
from core.context.domain.value_objects.graph_node import GraphNode
from core.context.domain.value_objects.graph_relationship_edge import GraphRelationshipEdge


@dataclass(frozen=True)
class GraphRelationships:
    """Aggregate Root for a graph node and its relationships.

    This Aggregate Root encapsulates:
    - The central node (GraphNode)
    - Neighbor nodes (GraphNeighbors collection)
    - Relationships connecting nodes (GraphRelationshipEdges collection)

    Domain Invariants:
    - node cannot be None
    - neighbors and relationships collections cannot be None (but can be empty)
    - All relationships must connect nodes that exist in the aggregate
    - No duplicate neighbor nodes (by ID)

    This is a pure domain Aggregate Root with NO serialization methods.
    Use GraphRelationshipsMapper in infrastructure layer for conversions.
    """

    node: GraphNode
    neighbors: GraphNeighbors
    relationships: GraphRelationshipEdges

    def __post_init__(self) -> None:
        """Validate graph relationships aggregate (fail-fast).

        Raises:
            ValueError: If validation fails
        """
        if self.node is None:
            raise ValueError("GraphRelationships node cannot be None")

        if self.neighbors is None:
            raise ValueError("GraphRelationships neighbors cannot be None")
        if self.relationships is None:
            raise ValueError("GraphRelationships relationships cannot be None")

        # Validate relationships connect existing nodes
        all_node_ids = {self.node.get_id_string()} | self.neighbors.get_all_ids()
        self.relationships.validate_against_nodes(all_node_ids)

    def get_neighbor_by_id(self, node_id: str) -> GraphNode | None:
        """Get neighbor node by ID.

        Args:
            node_id: Node identifier

        Returns:
            GraphNode if found, None otherwise
        """
        return self.neighbors.get_by_id(node_id)

    def get_relationships_for_node(self, node_id: str) -> list[GraphRelationshipEdge]:
        """Get all relationships involving a specific node.

        Args:
            node_id: Node identifier

        Returns:
            List of relationships where node_id is either from or to
        """
        return self.relationships.get_for_node(node_id)

    def get_outgoing_relationships(self, node_id: str) -> list[GraphRelationshipEdge]:
        """Get relationships where node_id is the source.

        Args:
            node_id: Source node identifier

        Returns:
            List of outgoing relationships
        """
        return self.relationships.get_outgoing(node_id)

    def get_incoming_relationships(self, node_id: str) -> list[GraphRelationshipEdge]:
        """Get relationships where node_id is the target.

        Args:
            node_id: Target node identifier

        Returns:
            List of incoming relationships
        """
        return self.relationships.get_incoming(node_id)

    def has_neighbor(self, node_id: str) -> bool:
        """Check if a node is a neighbor.

        Args:
            node_id: Node identifier

        Returns:
            True if node_id is in neighbors
        """
        return self.neighbors.has_neighbor(node_id)

    def neighbor_count(self) -> int:
        """Get number of neighbor nodes.

        Returns:
            Count of neighbors
        """
        return self.neighbors.count()

    def relationship_count(self) -> int:
        """Get number of relationships.

        Returns:
            Count of relationships
        """
        return self.relationships.count()

    @staticmethod
    def from_neo4j_result(
        node_data: dict[str, Any],
        neighbors_data: list[dict[str, Any]],
        node_type: str,
    ) -> "GraphRelationships":
        """Factory method to build GraphRelationships from Neo4j query result.

        This method delegates to GraphRelationshipsBuilder domain service
        to keep the aggregate root clean and focused.

        Args:
            node_data: Dictionary with node data from Neo4j
            neighbors_data: List of dictionaries with neighbor data from Neo4j
            node_type: Type of the main node (Project, Epic, Story, Task)

        Returns:
            GraphRelationships Aggregate Root

        Raises:
            ValueError: If data is invalid or invariants are violated
        """
        return GraphRelationshipsBuilder.build_from_neo4j_result(
            node_data=node_data,
            neighbors_data=neighbors_data,
            node_type=node_type,
        )

    def __str__(self) -> str:
        """Return human-readable representation."""
        return (
            f"GraphRelationships(node={self.node.get_id_string()}, "
            f"neighbors={self.neighbors.count()}, relationships={self.relationships.count()})"
        )
