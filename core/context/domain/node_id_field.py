"""NodeIdField Value Object - Represents the Neo4j property field name for node IDs."""

from dataclasses import dataclass

from core.context.domain.graph_label import GraphLabel


@dataclass(frozen=True)
class NodeIdField:
    """Value Object representing the Neo4j property field name for a node's identifier.

    This Value Object encapsulates domain knowledge about how different node types
    store their identifiers in Neo4j properties.

    Domain Invariants:
    - Project nodes use "project_id"
    - Epic nodes use "epic_id"
    - Story nodes use "story_id"
    - Task nodes use "task_id"
    - Unknown/fallback uses "id"

    This is a pure domain Value Object with NO serialization methods.
    """

    field_name: str

    def __post_init__(self) -> None:
        """Validate node ID field (fail-fast).

        Raises:
            ValueError: If validation fails
        """
        if not self.field_name or not self.field_name.strip():
            raise ValueError("NodeIdField field_name cannot be empty")

        valid_fields = {"project_id", "epic_id", "story_id", "task_id", "id"}
        if self.field_name not in valid_fields:
            raise ValueError(
                f"Invalid field_name: {self.field_name}. "
                f"Must be one of: {', '.join(sorted(valid_fields))}"
            )

    @staticmethod
    def from_graph_label(graph_label: GraphLabel) -> "NodeIdField":
        """Create NodeIdField from GraphLabel.

        Args:
            graph_label: GraphLabel enum value

        Returns:
            NodeIdField for the corresponding node type

        Raises:
            ValueError: If graph_label is not a valid node type
        """
        mapping: dict[GraphLabel, str] = {
            GraphLabel.PROJECT: "project_id",
            GraphLabel.EPIC: "epic_id",
            GraphLabel.STORY: "story_id",
            GraphLabel.TASK: "task_id",
        }

        field_name = mapping.get(graph_label, "id")
        return NodeIdField(field_name=field_name)

    @staticmethod
    def from_node_type(node_type: str) -> "NodeIdField":
        """Create NodeIdField from node type string.

        Args:
            node_type: Node type string (Project, Epic, Story, Task)

        Returns:
            NodeIdField for the corresponding node type

        Raises:
            ValueError: If node_type is empty or invalid
        """
        if not node_type or not node_type.strip():
            raise ValueError("node_type cannot be empty")

        mapping: dict[str, str] = {
            "Project": "project_id",
            "Epic": "epic_id",
            "Story": "story_id",
            "Task": "task_id",
        }

        field_name = mapping.get(node_type, "id")
        return NodeIdField(field_name=field_name)

    def to_string(self) -> str:
        """Convert to string representation.

        Explicit method following Tell, Don't Ask principle.

        Returns:
            String representation of field name
        """
        return self.field_name

    def __str__(self) -> str:
        """String representation for compatibility."""
        return self.to_string()

