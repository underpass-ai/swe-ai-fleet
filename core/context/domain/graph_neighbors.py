"""GraphNeighbors domain entity - Collection of neighbor nodes."""

from dataclasses import dataclass

from core.context.domain.value_objects.graph_node import GraphNode


@dataclass(frozen=True)
class GraphNeighbors:
    """Domain entity representing a collection of neighbor nodes.

    This entity encapsulates:
    - List of neighbor GraphNode instances
    - Validation (no duplicates by ID)
    - Query methods (get_by_id, has_neighbor, count)

    Domain Invariants:
    - nodes cannot be None (but can be empty)
    - No duplicate nodes (by ID)

    This is a pure domain entity with NO serialization methods.
    Use GraphNeighborsMapper in infrastructure layer for conversions.
    """

    nodes: list[GraphNode]

    def __post_init__(self) -> None:
        """Validate graph neighbors (fail-fast).

        Raises:
            ValueError: If validation fails
        """
        if self.nodes is None:
            raise ValueError("GraphNeighbors nodes cannot be None (use empty list [])")

        # Validate no duplicate neighbors (by ID)
        neighbor_ids = {n.get_id_string() for n in self.nodes}
        if len(neighbor_ids) != len(self.nodes):
            raise ValueError("GraphNeighbors cannot contain duplicate neighbor nodes")

    def get_by_id(self, node_id: str) -> GraphNode | None:
        """Get neighbor node by ID.

        Args:
            node_id: Node identifier

        Returns:
            GraphNode if found, None otherwise
        """
        for neighbor in self.nodes:
            if neighbor.has_id(node_id):
                return neighbor
        return None

    def has_neighbor(self, node_id: str) -> bool:
        """Check if a node is a neighbor.

        Args:
            node_id: Node identifier

        Returns:
            True if node_id is in neighbors
        """
        return any(n.has_id(node_id) for n in self.nodes)

    def count(self) -> int:
        """Get number of neighbor nodes.

        Returns:
            Count of neighbors
        """
        return len(self.nodes)

    def get_all_ids(self) -> set[str]:
        """Get all neighbor node IDs.

        Returns:
            Set of all neighbor node ID strings
        """
        return {n.get_id_string() for n in self.nodes}

    def find_node_by_id(self, node_id: str) -> GraphNode | None:
        """Find a neighbor node by ID.

        Args:
            node_id: Node identifier to search for

        Returns:
            GraphNode if found, None otherwise
        """
        return self.get_by_id(node_id)

    def __str__(self) -> str:
        """Return human-readable representation."""
        return f"GraphNeighbors(count={len(self.nodes)})"

