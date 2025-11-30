"""Node ID Field Mapping - Domain knowledge for mapping node types to their ID fields.

This module provides factory methods for creating NodeIdField Value Objects.
Deprecated: Use NodeIdField.from_node_type() or NodeIdField.from_graph_label() directly.
"""

from core.context.domain.node_id_field import NodeIdField


class NodeIdFieldMapping:
    """Domain knowledge for mapping node types to their ID field names.

    This class provides static factory methods for creating NodeIdField Value Objects.
    Prefer using NodeIdField.from_node_type() or NodeIdField.from_graph_label() directly.

    Domain Invariants:
    - Project nodes use "project_id"
    - Epic nodes use "epic_id"
    - Story nodes use "story_id"
    - Task nodes use "task_id"
    - Unknown/fallback uses "id"
    """

    @staticmethod
    def get_id_field(node_type: str) -> NodeIdField:
        """Get the NodeIdField Value Object for a given node type.

        Args:
            node_type: Node type (Project, Epic, Story, Task)

        Returns:
            NodeIdField Value Object for the corresponding node type

        Raises:
            ValueError: If node_type is empty or invalid
        """
        return NodeIdField.from_node_type(node_type)

    @staticmethod
    def get_allowed_node_types() -> tuple[str, ...]:
        """Get all allowed node types for graph queries.

        Returns:
            Tuple of valid node type strings
        """
        return ("Project", "Epic", "Story", "Task")

    @staticmethod
    def is_valid_node_type(node_type: str) -> bool:
        """Check if a node type is valid.

        Args:
            node_type: Node type to validate

        Returns:
            True if node_type is in the allowed list
        """
        return node_type in {"Project", "Epic", "Story", "Task"}

