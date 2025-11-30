"""Use case to get graph relationships from Neo4j.

Following DDD + Hexagonal Architecture:
- Use Case receives Port (interface) via DI
- Use Case orchestrates domain logic
- Returns domain Aggregate Root (not infrastructure concerns)
"""

import logging
from dataclasses import dataclass

from core.context.domain.graph_relationships import GraphRelationships
from core.context.ports.graph_query_port import GraphQueryPort

logger = logging.getLogger(__name__)


@dataclass
class GetGraphRelationshipsUseCase:
    """Use case to retrieve graph relationships from Neo4j.

    Following Hexagonal Architecture:
    - Receives GraphQueryPort (interface) via DI
    - Orchestrates query execution
    - Returns domain DTOs (NO infrastructure concerns)
    """

    graph_query: GraphQueryPort

    def execute(
        self,
        node_id: str,
        node_type: str,
        depth: int = 2,
    ) -> GraphRelationships:
        """Execute graph relationships query.

        Args:
            node_id: Node identifier
            node_type: Node type (Project, Epic, Story, Task)
            depth: Traversal depth (1-3)

        Returns:
            GraphRelationships Aggregate Root with node, neighbors, and relationships

        Raises:
            ValueError: If node not found or invalid parameters
        """
        # Validate inputs (fail-fast)
        if not node_id or not node_id.strip():
            raise ValueError("node_id is required and cannot be empty")

        if node_type not in ["Project", "Epic", "Story", "Task"]:
            raise ValueError(f"Invalid node_type: {node_type}. Must be Project, Epic, Story, or Task")

        depth = min(max(depth, 1), 3)  # Clamp depth between 1 and 3

        # Get graph relationships via port (infrastructure abstraction)
        # Port handles query construction and result parsing
        result = self.graph_query.get_graph_relationships(
            node_id=node_id,
            node_type=node_type,
            depth=depth,
        )

        if not result:
            raise ValueError(f"Node not found: {node_id} (type: {node_type})")

        # Build Aggregate Root using factory method (encapsulates construction logic)
        aggregate = GraphRelationships.from_neo4j_result(
            node_data=result["node_data"],
            neighbors_data=result["neighbors_data"],
            node_type=node_type,
        )

        logger.info(
            f"GetGraphRelationships: node={aggregate.node.id.value}, "
            f"neighbors={aggregate.neighbor_count()}, relationships={aggregate.relationship_count()}"
        )

        return aggregate

