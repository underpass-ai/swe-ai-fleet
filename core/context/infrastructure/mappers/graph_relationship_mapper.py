"""Mapper for GraphRelationship - Infrastructure layer.

Handles conversion between domain GraphRelationship and Neo4j-specific formats.
"""

from typing import Any

from core.context.domain.graph_relationship import GraphRelationship


class GraphRelationshipMapper:
    """Mapper for GraphRelationship conversions."""

    @staticmethod
    def to_dict(relationship: GraphRelationship) -> dict[str, Any]:
        """Convert GraphRelationship to dictionary representation.

        Args:
            relationship: GraphRelationship domain value object

        Returns:
            Dictionary with string values (for serialization)
        """
        return {
            "src_id": relationship.src_id,
            "rel_type": relationship.rel_type.value,
            "dst_id": relationship.dst_id,
            "src_labels": [label.value for label in relationship.src_labels],
            "dst_labels": [label.value for label in relationship.dst_labels],
        }

    @staticmethod
    def to_cypher_pattern(relationship: GraphRelationship, properties: dict[str, Any] | None = None) -> str:
        """Generate Cypher pattern for creating/merging this relationship in Neo4j.

        Args:
            relationship: GraphRelationship domain value object
            properties: Optional properties dict to attach to the relationship

        Returns:
            Cypher MATCH + MERGE pattern

        Example:
            MATCH (a:Story {id:$src}), (b:PlanVersion {id:$dst})
            MERGE (a)-[r:HAS_PLAN]->(b) SET r += $props
        """
        # Build label expressions
        src_label_expr = ":" + ":".join(sorted({str(label) for label in relationship.src_labels}))
        dst_label_expr = ":" + ":".join(sorted({str(label) for label in relationship.dst_labels}))

        # Build Cypher pattern
        rel_type_str = str(relationship.rel_type)

        if properties:
            return (
                f"MATCH (a{src_label_expr} {{id:$src}}), (b{dst_label_expr} {{id:$dst}}) "
                f"MERGE (a)-[r:{rel_type_str}]->(b) SET r += $props"
            )
        else:
            return (
                f"MATCH (a{src_label_expr} {{id:$src}}), (b{dst_label_expr} {{id:$dst}}) "
                f"MERGE (a)-[r:{rel_type_str}]->(b)"
            )

    @staticmethod
    def to_cypher_params(
        relationship: GraphRelationship,
        properties: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Generate Cypher parameters for the relationship.

        Args:
            relationship: GraphRelationship domain value object
            properties: Optional properties dict

        Returns:
            Dictionary with 'src', 'dst', and optionally 'props' keys
        """
        params = {
            "src": relationship.src_id,
            "dst": relationship.dst_id,
        }

        if properties:
            params["props"] = properties

        return params

