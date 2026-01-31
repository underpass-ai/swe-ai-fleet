"""Graph command port - Application layer interface for graph writes.

This port defines the contract for writing domain entities to the graph database.
It works with domain entities, NOT with Neo4j-specific primitives (labels, dicts).
"""

from typing import Any, Protocol

from core.context.domain.epic import Epic
from core.context.domain.graph_label import GraphLabel
from core.context.domain.graph_relationship import GraphRelationship
from core.context.domain.phase_transition import PhaseTransition
from core.context.domain.plan_approval import PlanApproval
from core.context.domain.plan_version import PlanVersion
from core.context.domain.project import Project
from core.context.domain.story import Story
from core.context.domain.task import Task


class GraphCommandPort(Protocol):
    """Port for writing domain entities to graph database.

    This port follows Hexagonal Architecture principles:
    - Application layer depends on this port (interface)
    - Infrastructure adapter implements this port
    - Port works with domain entities, NOT primitives

    Hierarchy support: Project → Epic → Story → Task
    """

    def init_constraints(self, labels: list[GraphLabel]) -> None:
        """Initialize unique constraints for entity types.

        Args:
            labels: List of GraphLabel enums to create constraints for
        """
        ...

    def save_project(self, project: Project) -> None:
        """Save Project entity to graph (root of hierarchy).

        Args:
            project: Project domain entity
        """
        ...

    def save_epic(self, epic: Epic) -> None:
        """Save Epic entity to graph.

        Domain Invariant: Epic MUST have project_id.

        Args:
            epic: Epic domain entity with project_id

        Raises:
            ValueError: If epic.project_id is empty
        """
        ...

    def save_story(self, story: Story) -> None:
        """Save Story entity to graph.

        Domain Invariant: Story MUST have epic_id.

        Args:
            story: Story domain entity with epic_id

        Raises:
            ValueError: If story.epic_id is empty
        """
        ...

    def save_plan_version(self, plan: PlanVersion) -> None:
        """Save PlanVersion entity to graph.

        Args:
            plan: PlanVersion domain entity
        """
        ...

    def save_task(self, task: Task) -> None:
        """Save Task entity to graph.

        Args:
            task: Task domain entity
        """
        ...

    def save_plan_approval(self, approval: PlanApproval) -> None:
        """Save PlanApproval entity to graph (audit trail).

        Args:
            approval: PlanApproval domain entity
        """
        ...

    def save_phase_transition(self, transition: PhaseTransition) -> None:
        """Save PhaseTransition entity to graph (audit trail).

        Args:
            transition: PhaseTransition domain entity
        """
        ...

    def upsert_entity(
        self,
        label: str,
        id: str,
        properties: dict[str, Any] | None = None,
    ) -> None:
        """Upsert an entity by label and id (escape hatch for generic writes).

        Args:
            label: Neo4j label (e.g. "Event")
            id: Entity identifier
            properties: Optional properties
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
