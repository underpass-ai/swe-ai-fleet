"""RelationshipError domain exception - Represents invalid graph relationship errors."""

from core.context.domain.value_objects.graph_relationship_edge import GraphRelationshipEdge


class RelationshipError(ValueError):
    """Domain exception for invalid graph relationships.

    This exception is raised when a GraphRelationshipEdge connects nodes
    that do not exist in the current aggregate.

    Domain Invariants:
    - from_node_id and to_node_id cannot be empty
    - valid_node_ids cannot be None (but can be empty)

    This is a pure domain exception with NO serialization methods.
    Use RelationshipErrorMapper in infrastructure layer for external formatting.
    """

    def __init__(
        self,
        relationship: GraphRelationshipEdge,
        valid_node_ids: set[str],
    ) -> None:
        """Initialize RelationshipError.

        Args:
            relationship: GraphRelationshipEdge that failed validation
            valid_node_ids: Set of valid node ID strings in the aggregate

        Raises:
            ValueError: If relationship or valid_node_ids are invalid
        """
        if relationship is None:
            raise ValueError("RelationshipError relationship cannot be None")

        if valid_node_ids is None:
            raise ValueError("RelationshipError valid_node_ids cannot be None (use empty set)")

        from_id = relationship.from_node.get_id_string()
        to_id = relationship.to_node.get_id_string()

        if not from_id or not from_id.strip():
            raise ValueError("RelationshipError from_node_id cannot be empty")

        if not to_id or not to_id.strip():
            raise ValueError("RelationshipError to_node_id cannot be empty")

        self.relationship = relationship
        self.valid_node_ids = valid_node_ids
        self.from_node_id = from_id
        self.to_node_id = to_id

        message = (
            f"Relationship connects invalid nodes: from_node.id='{from_id}', "
            f"to_node.id='{to_id}'. Valid node IDs: {valid_node_ids}"
        )
        super().__init__(message)

