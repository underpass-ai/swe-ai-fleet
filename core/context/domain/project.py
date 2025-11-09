"""Project domain entity - Root of work hierarchy."""

from dataclasses import dataclass

from .entity_ids.epic_id import EpicId
from .entity_ids.project_id import ProjectId
from .graph_label import GraphLabel
from .graph_relation_type import GraphRelationType
from .graph_relationship import GraphRelationship
from .project_status import ProjectStatus


@dataclass(frozen=True)
class Project:
    """Project domain entity - Top-level work container.

    A Project groups related Epics and represents a complete product/initiative.
    This is the root of the work hierarchy in SWE AI Fleet.

    Hierarchy: Project → Epic → Story → Task

    DOMAIN INVARIANT: Project is the root. All work traces back to a Project.
    NO orphan epics allowed.

    Business Rules:
    - Projects are created by Product Owners
    - Projects have a name, description, and owner
    - Projects can be in various states (active, planning, completed, etc.)
    - All epics MUST belong to a project

    This is a pure domain entity with NO serialization methods.
    Use ProjectMapper in infrastructure layer for conversions.
    """

    project_id: ProjectId
    name: str
    description: str = ""
    status: ProjectStatus = ProjectStatus.ACTIVE
    owner: str = ""  # PO or project owner (can be empty initially)
    created_at_ms: int = 0

    def __post_init__(self) -> None:
        """Validate project (fail-fast).

        Domain invariants:
        - Project name cannot be empty
        - created_at_ms cannot be negative

        Raises:
            ValueError: If validation fails
        """
        if not self.name or not self.name.strip():
            raise ValueError("Project name cannot be empty")

        if self.created_at_ms < 0:
            raise ValueError("created_at_ms cannot be negative")

    def is_active(self) -> bool:
        """Check if project is active.

        Returns:
            True if status indicates active work
        """
        return self.status.is_active_work()

    def is_completed(self) -> bool:
        """Check if project is completed.

        Returns:
            True if status is completed
        """
        return self.status == ProjectStatus.COMPLETED

    def is_terminal(self) -> bool:
        """Check if project is in terminal state (no further work expected).

        Returns:
            True if in terminal state
        """
        return self.status.is_terminal()

    def get_relationship_to_epic(self, epic_id: EpicId) -> GraphRelationship:
        """Get relationship from Project to Epic.

        Args:
            epic_id: ID of the epic that belongs to this project

        Returns:
            GraphRelationship connecting Project→Epic
        """
        return GraphRelationship(
            src_id=self.project_id.to_string(),
            src_labels=[GraphLabel.PROJECT],
            rel_type=GraphRelationType.HAS_EPIC,
            dst_id=epic_id.to_string(),
            dst_labels=[GraphLabel.EPIC],
            properties=None,
        )

    def to_graph_properties(self) -> dict[str, str]:
        """Convert Project to Neo4j node properties.

        Returns:
            Dictionary of properties for Neo4j node
        """
        return {
            "project_id": self.project_id.to_string(),
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "owner": self.owner,
            "created_at_ms": str(self.created_at_ms),
        }

