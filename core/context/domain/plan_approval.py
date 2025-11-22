"""PlanApproval domain entity."""

from dataclasses import dataclass

from core.context.domain.entity_ids.plan_id import PlanId
from core.context.domain.entity_ids.story_id import StoryId


@dataclass(frozen=True)
class PlanApproval:
    """Domain entity representing a plan approval event.

    This entity captures when a plan is approved (audit trail).
    Used for tracking decision history in the knowledge graph.

    Immutable (frozen=True) following DDD principles.
    """

    plan_id: PlanId
    story_id: StoryId
    approved_by: str
    timestamp: str  # ISO format timestamp

    def __post_init__(self) -> None:
        """Validate plan approval (fail-fast).

        Raises:
            ValueError: If validation fails
        """
        if not self.approved_by or not self.approved_by.strip():
            raise ValueError("approved_by cannot be empty")
        if not self.timestamp or not self.timestamp.strip():
            raise ValueError("timestamp cannot be empty")

    def get_entity_id(self) -> str:
        """Get unique entity ID for Neo4j.

        Returns:
            Composite ID: plan_id:timestamp
        """
        return f"{self.plan_id.value}:{self.timestamp}"

    def to_graph_properties(self) -> dict[str, str]:
        """Convert to properties for Neo4j graph storage.

        Returns:
            Dictionary with properties for Neo4j node
        """
        return {
            "plan_id": self.plan_id.value,
            "story_id": self.story_id.value,
            "approved_by": self.approved_by,
            "timestamp": self.timestamp,
        }

    def get_graph_label(self) -> str:
        """Get Neo4j label for this entity.

        Returns:
            GraphLabel string
        """
        return "PlanApproval"

    def get_log_context(self) -> dict[str, str]:
        """Get structured logging context (Tell, Don't Ask).

        Returns:
            Dictionary with logging fields
        """
        return {
            "plan_id": self.plan_id.to_string(),
            "story_id": self.story_id.to_string(),
            "approved_by": self.approved_by,
        }

