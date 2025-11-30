"""Mapper for Graph Relationships - Infrastructure layer.

Handles conversion between domain Aggregate Root and protobuf messages.
Following Hexagonal Architecture: Infrastructure layer responsibility.
"""

from core.context.domain.graph_relationships import GraphRelationships
from services.context.gen import context_pb2


class GraphRelationshipsProtobufMapper:
    """Mapper for Graph Relationships conversions.

    Infrastructure Layer Responsibility:
    - Convert domain Aggregate Root to protobuf messages
    - Convert protobuf messages to domain Aggregate Root (if needed)
    - Handle serialization details (infrastructure concern)
    """

    @staticmethod
    def to_protobuf_response(
        aggregate: GraphRelationships,
    ) -> context_pb2.GetGraphRelationshipsResponse:
        """Convert domain Aggregate Root to protobuf response.

        Args:
            aggregate: GraphRelationships Aggregate Root

        Returns:
            GetGraphRelationshipsResponse protobuf message
        """
        # Map main node
        graph_node = context_pb2.GraphNode(
            id=aggregate.node.id.value,
            labels=[label.value for label in aggregate.node.labels],
            properties=aggregate.node.properties.properties,
            type=aggregate.node.node_type.value,
            title=aggregate.node.title.value,
        )

        # Map neighbor nodes
        neighbor_nodes = [
            context_pb2.GraphNode(
                id=n.id.value,
                labels=[label.value for label in n.labels],
                properties=n.properties.properties,
                type=n.node_type.value,
                title=n.title.value,
            )
            for n in aggregate.neighbors.nodes
        ]

        # Map relationships
        relationships = [
            context_pb2.GraphRelationship(
                from_node_id=r.from_node.id.value,
                to_node_id=r.to_node.id.value,
                type=r.relationship_type.value,
                properties=r.properties.properties,
            )
            for r in aggregate.relationships.edges
        ]

        return context_pb2.GetGraphRelationshipsResponse(
            node=graph_node,
            neighbors=neighbor_nodes,
            relationships=relationships,
            success=True,
            message="Graph relationships retrieved successfully",
        )

    @staticmethod
    def to_error_response(
        message: str,
        success: bool = False,
    ) -> context_pb2.GetGraphRelationshipsResponse:
        """Create error response protobuf message.

        Args:
            message: Error message
            success: Success flag (default: False)

        Returns:
            GetGraphRelationshipsResponse with error
        """
        return context_pb2.GetGraphRelationshipsResponse(
            success=success,
            message=message,
        )

