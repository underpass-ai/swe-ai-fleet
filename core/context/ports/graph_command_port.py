"""Graph command port - Application layer interface for graph writes.

This port defines the contract for writing domain entities to the graph database.
It works with domain entities, NOT with Neo4j-specific primitives (labels, dicts).
"""

from typing import Protocol

from core.context.domain.story import Story
from core.context.domain.plan_version import PlanVersion
from core.context.domain.graph_relationship import GraphRelationship
from core.context.domain.graph_label import GraphLabel


class GraphCommandPort(Protocol):
    """Port for writing domain entities to graph database.

    This port follows Hexagonal Architecture principles:
    - Application layer depends on this port (interface)
    - Infrastructure adapter implements this port
    - Port works with domain entities, NOT primitives
    """

    def init_constraints(self, labels: list[GraphLabel]) -> None:
        """Initialize unique constraints for entity types.

        Args:
            labels: List of GraphLabel enums to create constraints for
        """
        ...

    def save_story(self, story: Story) -> None:
        """Save Story entity to graph.

        Args:
            story: Story domain entity
        """
        ...

    def save_plan_version(self, plan: PlanVersion) -> None:
        """Save PlanVersion entity to graph.

        Args:
            plan: PlanVersion domain entity
        """
        ...

    def create_relationship(self, relationship: GraphRelationship) -> None:
        """Create relationship between entities in graph.

        Args:
            relationship: GraphRelationship domain value object
        """
        ...

    def execute_write(self, cypher: str, params: dict) -> list:
        """Execute raw Cypher write query (escape hatch for complex operations).

        Args:
            cypher: Cypher query string
            params: Query parameters

        Returns:
            Query results
        """
        ...
