"""GraphRelationshipsBuilder domain service - Builds GraphRelationships from Neo4j data.

This domain service encapsulates all logic for constructing GraphRelationships
Aggregate Root from raw Neo4j query results.

Following DDD principles:
- Pure domain logic (no infrastructure dependencies)
- Stateless service (all methods are static)
- Single responsibility: building GraphRelationships aggregates
"""

from typing import Any

from core.context.domain.graph_node_type import GraphNodeType
from core.context.domain.graph_relation_type import GraphRelationType
from core.context.domain.node_id_field import NodeIdField
from core.context.domain.value_objects.graph_node import GraphNode
from core.context.domain.value_objects.graph_relationship_edge import GraphRelationshipEdge
from core.context.domain.value_objects.graph_relationship_edge_properties import (
    GraphRelationshipEdgeProperties,
)
from core.context.domain.value_objects.node_id import NodeId
from core.context.domain.value_objects.node_label import NodeLabel
from core.context.domain.value_objects.node_properties import NodeProperties
from core.context.domain.value_objects.node_title import NodeTitle
from core.context.domain.value_objects.node_type import NodeType


class GraphRelationshipsBuilder:
    """Domain service for building GraphRelationships Aggregate Root from Neo4j data.

    This service encapsulates all construction logic, making GraphRelationships
    a pure aggregate root without factory method complexity.

    All methods are static - this is a stateless domain service.
    """

    @staticmethod
    def build_from_neo4j_result(
        node_data: dict[str, Any],
        neighbors_data: list[dict[str, Any]],
        node_type: str,
    ) -> "GraphRelationships":
        """Build GraphRelationships Aggregate Root from Neo4j query result.

        Args:
            node_data: Dictionary with node data from Neo4j
            neighbors_data: List of dictionaries with neighbor data from Neo4j
            node_type: Type of the main node (Project, Epic, Story, Task)

        Returns:
            GraphRelationships Aggregate Root

        Raises:
            ValueError: If data is invalid or invariants are violated
        """
        main_node, main_node_id = GraphRelationshipsBuilder._build_main_node(
            node_data, node_type
        )
        neighbors, relationships = GraphRelationshipsBuilder._build_neighbors_and_relationships(
            neighbors_data, main_node, main_node_id
        )
        return GraphRelationshipsBuilder._create_aggregate(main_node, neighbors, relationships)

    @staticmethod
    def _build_main_node(
        node_data: dict[str, Any], node_type: str
    ) -> tuple[GraphNode, NodeId]:
        """Build main node Value Object from Neo4j data.

        Args:
            node_data: Dictionary with node data from Neo4j
            node_type: Type of the main node (Project, Epic, Story, Task)

        Returns:
            Tuple of (GraphNode, NodeId)

        Raises:
            ValueError: If title is missing
        """
        node_props = node_data.get("properties", {})
        node_title = node_data.get("title")
        if not node_title:
            raise ValueError(f"Node title is required but missing for node: {node_data.get('id')}")

        main_node_id = NodeId(value=node_data["id"])
        main_node = GraphNode(
            id=main_node_id,
            labels=[NodeLabel(value=label) for label in node_data.get("labels", [])],
            properties=NodeProperties(properties=node_props),
            node_type=NodeType(value=node_type),
            title=NodeTitle(value=node_title),
        )
        return main_node, main_node_id

    @staticmethod
    def _build_neighbors_and_relationships(
        neighbors_data: list[dict[str, Any]],
        main_node: GraphNode,
        main_node_id: NodeId,
    ) -> tuple[list[GraphNode], list[GraphRelationshipEdge]]:
        """Build neighbor nodes and relationships from Neo4j data.

        Args:
            neighbors_data: List of dictionaries with neighbor data from Neo4j
            main_node: The main node in the aggregate
            main_node_id: NodeId of the main node

        Returns:
            Tuple of (list[GraphNode], list[GraphRelationshipEdge])
        """
        neighbor_nodes: list[GraphNode] = []
        relationships: list[GraphRelationshipEdge] = []
        seen_neighbors: dict[str, GraphNode] = {}

        for neighbor_info in neighbors_data:
            neighbor = neighbor_info.get("node")
            if not neighbor:
                continue

            neighbor_node = GraphRelationshipsBuilder._build_neighbor_node(neighbor)
            if not neighbor_node:
                continue

            neighbor_id_str = neighbor_node.get_id_string()
            if neighbor_id_str in seen_neighbors:
                continue

            neighbor_nodes.append(neighbor_node)
            seen_neighbors[neighbor_id_str] = neighbor_node

            # Extract relationships for this neighbor
            neighbor_relationships = GraphRelationshipsBuilder._extract_relationships(
                neighbor_info=neighbor_info,
                main_node=main_node,
                current_neighbor=neighbor_node,
                current_neighbor_id=neighbor_node.id,
                seen_neighbors=seen_neighbors,
                default_from_id=main_node_id,
                default_to_id=neighbor_node.id,
            )
            relationships.extend(neighbor_relationships)

        return neighbor_nodes, relationships

    @staticmethod
    def _build_neighbor_node(neighbor: dict[str, Any]) -> GraphNode | None:
        """Build a neighbor GraphNode from Neo4j data.

        Args:
            neighbor: Dictionary with neighbor node data from Neo4j

        Returns:
            GraphNode if valid, None if type cannot be determined

        Raises:
            ValueError: If title is missing
        """
        neighbor_props = neighbor.get("properties", {})
        neighbor_labels = neighbor.get("labels", [])

        neighbor_node_type = GraphRelationshipsBuilder._determine_neighbor_type(neighbor_labels)
        if not neighbor_node_type:
            return None

        neighbor_id_str = GraphRelationshipsBuilder._get_neighbor_id(neighbor, neighbor_node_type)
        if not neighbor_id_str:
            return None

        neighbor_title = neighbor.get("title")
        if not neighbor_title:
            raise ValueError(f"Neighbor title is required but missing for node: {neighbor_id_str}")

        neighbor_node_id = NodeId(value=neighbor_id_str)
        return GraphNode(
            id=neighbor_node_id,
            labels=[NodeLabel(value=label) for label in neighbor_labels],
            properties=NodeProperties(properties=neighbor_props),
            node_type=NodeType(value=neighbor_node_type.value),
            title=NodeTitle(value=neighbor_title),
        )

    @staticmethod
    def _determine_neighbor_type(labels: list[str]) -> GraphNodeType | None:
        """Determine neighbor node type from Neo4j labels.

        Args:
            labels: List of Neo4j label strings

        Returns:
            GraphNodeType if found, None otherwise
        """
        for label in labels:
            neighbor_node_type = GraphNodeType.from_label(label)
            if neighbor_node_type:
                return neighbor_node_type
        return None

    @staticmethod
    def _get_neighbor_id(neighbor: dict[str, Any], neighbor_type: GraphNodeType) -> str | None:
        """Get neighbor ID according to node type.

        Args:
            neighbor: Dictionary with neighbor node data
            neighbor_type: GraphNodeType of the neighbor

        Returns:
            Neighbor ID string if found, None otherwise
        """
        id_field = NodeIdField.from_node_type(neighbor_type.value)
        return neighbor.get(id_field.to_string()) or neighbor.get("id")

    @staticmethod
    def _extract_relationships(
        neighbor_info: dict[str, Any],
        main_node: GraphNode,
        current_neighbor: GraphNode,
        current_neighbor_id: NodeId,
        seen_neighbors: dict[str, GraphNode],
        default_from_id: NodeId,
        default_to_id: NodeId,
    ) -> list[GraphRelationshipEdge]:
        """Extract relationships from a neighbor's data.

        Args:
            neighbor_info: Dictionary with neighbor info including relationships
            main_node: The main node in the aggregate
            current_neighbor: The current neighbor node being processed
            current_neighbor_id: NodeId of the current neighbor
            seen_neighbors: Dictionary of already processed neighbors by ID
            default_from_id: Default from NodeId if not in rel_data
            default_to_id: Default to NodeId if not in rel_data

        Returns:
            List of GraphRelationshipEdge instances
        """
        relationships: list[GraphRelationshipEdge] = []
        rels = neighbor_info.get("relationships", [])

        for rel in rels:
            relationship = GraphRelationshipsBuilder._build_relationship(
                rel_data=rel,
                main_node=main_node,
                current_neighbor=current_neighbor,
                current_neighbor_id=current_neighbor_id,
                seen_neighbors=seen_neighbors,
                default_from_id=default_from_id,
                default_to_id=default_to_id,
            )
            # Skip if relationship cannot be built (valid case: new nodes with type project may have no relationships)
            if relationship:
                relationships.append(relationship)

        return relationships

    @staticmethod
    def _build_relationship(
        rel_data: dict[str, Any],
        main_node: GraphNode,
        current_neighbor: GraphNode,
        current_neighbor_id: NodeId,
        seen_neighbors: dict[str, GraphNode],
        default_from_id: NodeId,
        default_to_id: NodeId,
    ) -> GraphRelationshipEdge | None:
        """Build a GraphRelationshipEdge from Neo4j relationship data.

        Args:
            rel_data: Dictionary with relationship data from Neo4j
            main_node: The main node in the aggregate
            current_neighbor: The current neighbor node being processed
            current_neighbor_id: NodeId of the current neighbor
            seen_neighbors: Dictionary of already processed neighbors by ID
            default_from_id: Default from NodeId if not in rel_data
            default_to_id: Default to NodeId if not in rel_data

        Returns:
            GraphRelationshipEdge if nodes are found, None otherwise
        """
        rel_type_str = rel_data.get("type", "RELATED")
        rel_from_id = rel_data.get("from") or default_from_id.value
        rel_to_id = rel_data.get("to") or default_to_id.value
        rel_props = rel_data.get("properties", {})

        # Find from_node using domain methods (Tell, Don't Ask)
        from_node = GraphRelationshipsBuilder._find_node_by_id(
            node_id=rel_from_id,
            main_node=main_node,
            current_neighbor=current_neighbor,
            current_neighbor_id=current_neighbor_id,
            seen_neighbors=seen_neighbors,
        )

        # Find to_node using domain methods (Tell, Don't Ask)
        to_node = GraphRelationshipsBuilder._find_node_by_id(
            node_id=rel_to_id,
            main_node=main_node,
            current_neighbor=current_neighbor,
            current_neighbor_id=current_neighbor_id,
            seen_neighbors=seen_neighbors,
        )

        # Skip if nodes not found (shouldn't happen, but defensive)
        if not from_node or not to_node:
            return None

        # Map relationship type string to enum (with fallback)
        try:
            rel_type = GraphRelationType(rel_type_str)
        except ValueError:
            # If not a known type, use default fallback
            # This is a limitation - we might need to extend GraphRelationType
            rel_type = GraphRelationType.RELATES_TO  # Default fallback

        # Create properties Value Object
        edge_properties = GraphRelationshipEdgeProperties(properties=rel_props)

        return GraphRelationshipEdge(
            from_node=from_node,
            to_node=to_node,
            relationship_type=rel_type,
            properties=edge_properties,
        )

    @staticmethod
    def _find_node_by_id(
        node_id: str,
        main_node: GraphNode,
        current_neighbor: GraphNode,
        current_neighbor_id: NodeId,
        seen_neighbors: dict[str, GraphNode],
    ) -> GraphNode | None:
        """Find a node by ID in the aggregate.

        This method encapsulates the search logic, following Tell, Don't Ask principle.
        It asks nodes to identify themselves rather than checking their IDs externally.

        Args:
            node_id: Node identifier to search for (string)
            main_node: The main node in the aggregate
            current_neighbor: The current neighbor node being processed
            current_neighbor_id: NodeId of the current neighbor
            seen_neighbors: Dictionary of already processed neighbors by ID

        Returns:
            GraphNode if found, None otherwise
        """
        # Check main node (Tell, Don't Ask)
        if main_node.has_id(node_id):
            return main_node

        # Check current neighbor (Tell, Don't Ask)
        # Use NodeId comparison for current neighbor
        if current_neighbor_id.value == node_id:
            return current_neighbor

        # Check seen neighbors
        return seen_neighbors.get(node_id)

    @staticmethod
    def _create_aggregate(
        main_node: GraphNode,
        neighbor_nodes: list[GraphNode],
        relationships: list[GraphRelationshipEdge],
    ) -> "GraphRelationships":
        """Create GraphRelationships Aggregate Root from components.

        Args:
            main_node: The main node
            neighbor_nodes: List of neighbor nodes
            relationships: List of relationship edges

        Returns:
            GraphRelationships Aggregate Root
        """
        from core.context.domain.graph_neighbors import GraphNeighbors
        from core.context.domain.graph_relationship_edges import GraphRelationshipEdges
        from core.context.domain.graph_relationships import GraphRelationships

        neighbors_collection = GraphNeighbors(nodes=neighbor_nodes)
        relationships_collection = GraphRelationshipEdges(edges=relationships)

        return GraphRelationships(
            node=main_node,
            neighbors=neighbors_collection,
            relationships=relationships_collection,
        )

