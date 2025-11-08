"""Epic domain entity - Aggregate root for grouping related stories."""

from dataclasses import dataclass

from .entity_ids.epic_id import EpicId
from .entity_ids.story_id import StoryId
from .epic_status import EpicStatus
from .graph_label import GraphLabel
from .graph_relation_type import GraphRelationType
from .graph_relationship import GraphRelationship


@dataclass(frozen=True)
class Epic:
    """Epic domain entity - groups related User Stories.

    An Epic represents a large body of work that can be broken down
    into multiple User Stories. Epics provide high-level context and
    help with:
    - Strategic planning
    - Release planning
    - Progress tracking across multiple stories
    - Architectural context for agents

    Hierarchy: Epic → Story → Task

    This is a pure domain entity with NO serialization methods.
    Use EpicMapper in infrastructure layer for conversions.
    """

    epic_id: EpicId
    title: str
    description: str = ""
    status: EpicStatus = EpicStatus.ACTIVE
    created_at_ms: int = 0

    def __post_init__(self) -> None:
        """Validate epic (fail-fast).

        Raises:
            ValueError: If validation fails
        """
        if not self.title or not self.title.strip():
            raise ValueError("Epic title cannot be empty")

        if self.created_at_ms < 0:
            raise ValueError("created_at_ms cannot be negative")

    def is_active(self) -> bool:
        """Check if epic is active.

        Returns:
            True if status is active or in_progress
        """
        return self.status.is_active_work()

    def is_completed(self) -> bool:
        """Check if epic is completed.

        Returns:
            True if status is completed
        """
        return self.status == EpicStatus.COMPLETED

    def is_terminal(self) -> bool:
        """Check if epic is in terminal state.

        Returns:
            True if no further work expected
        """
        return self.status.is_terminal()

    def get_relationship_to_story(self, story_id: StoryId) -> GraphRelationship:
        """Get relationship from Epic to Story.

        Args:
            story_id: ID of the story that belongs to this epic

        Returns:
            GraphRelationship connecting Epic→Story
        """
        return GraphRelationship(
            src_id=self.epic_id.to_string(),
            src_labels=[GraphLabel.EPIC],
            rel_type=GraphRelationType.CONTAINS_STORY,
            dst_id=story_id.to_string(),
            dst_labels=[GraphLabel.STORY],
            properties=None,
        )

    def to_graph_properties(self) -> dict[str, str]:
        """Convert Epic to Neo4j node properties.

        Returns:
            Dictionary of properties for Neo4j node
        """
        return {
            "epic_id": self.epic_id.to_string(),
            "title": self.title,
            "description": self.description,
            "status": self.status.value,  # Enum to string
            "created_at_ms": str(self.created_at_ms),
        }

