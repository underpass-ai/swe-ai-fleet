"""PhaseTransition domain entity."""

from dataclasses import dataclass

from core.context.domain.entity_ids.story_id import StoryId


@dataclass(frozen=True)
class PhaseTransition:
    """Domain entity representing a story phase transition event.

    This entity captures when a story transitions between phases (audit trail).
    Used for tracking phase history in the knowledge graph.

    Immutable (frozen=True) following DDD principles.
    """

    story_id: StoryId
    from_phase: str
    to_phase: str
    timestamp: str  # ISO format timestamp

    def __post_init__(self) -> None:
        """Validate phase transition (fail-fast).

        Raises:
            ValueError: If validation fails
        """
        if not self.from_phase or not self.from_phase.strip():
            raise ValueError("from_phase cannot be empty")
        if not self.to_phase or not self.to_phase.strip():
            raise ValueError("to_phase cannot be empty")
        if not self.timestamp or not self.timestamp.strip():
            raise ValueError("timestamp cannot be empty")

    def get_entity_id(self) -> str:
        """Get unique entity ID for Neo4j.

        Returns:
            Composite ID: story_id:timestamp
        """
        return f"{self.story_id.value}:{self.timestamp}"

    def to_graph_properties(self) -> dict[str, str]:
        """Convert to properties for Neo4j graph storage.

        Returns:
            Dictionary with properties for Neo4j node
        """
        return {
            "story_id": self.story_id.value,
            "from_phase": self.from_phase,
            "to_phase": self.to_phase,
            "timestamp": self.timestamp,
        }

    def get_graph_label(self) -> str:
        """Get Neo4j label for this entity.

        Returns:
            GraphLabel string
        """
        return "PhaseTransition"

    def get_log_context(self) -> dict[str, str]:
        """Get structured logging context (Tell, Don't Ask).

        Returns:
            Dictionary with logging fields
        """
        return {
            "story_id": self.story_id.to_string(),
            "from_phase": self.from_phase,
            "to_phase": self.to_phase,
        }

