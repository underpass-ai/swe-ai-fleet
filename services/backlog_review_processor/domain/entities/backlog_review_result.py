"""BacklogReviewResult domain entity."""

from dataclasses import dataclass
from datetime import datetime

from backlog_review_processor.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from backlog_review_processor.domain.value_objects.identifiers.story_id import StoryId
from backlog_review_processor.domain.value_objects.statuses.backlog_review_role import (
    BacklogReviewRole,
)


@dataclass(frozen=True)
class BacklogReviewResult:
    """
    Domain Entity: Result of a backlog review agent deliberation.

    Encapsulates the complete context of an agent's deliberation result
    for a specific story within a backlog review ceremony.

    Attributes:
        ceremony_id: Ceremony identifier
        story_id: Story identifier
        agent_id: Agent identifier
        role: Council role (BacklogReviewRole enum)
        proposal: Full proposal/deliberation from agent (dict or str)
        reviewed_at: Timestamp when deliberation was reviewed
    """

    ceremony_id: BacklogReviewCeremonyId
    story_id: StoryId
    agent_id: str
    role: BacklogReviewRole
    proposal: dict | str
    reviewed_at: datetime

    def __post_init__(self) -> None:
        """Validate domain entity (fail-fast).

        Raises:
            ValueError: If validation fails
        """
        if not self.agent_id or not self.agent_id.strip():
            raise ValueError("agent_id cannot be empty")

        if not isinstance(self.role, BacklogReviewRole):
            raise ValueError(
                f"role must be a BacklogReviewRole enum, got {type(self.role)}"
            )

        if not isinstance(self.ceremony_id, BacklogReviewCeremonyId):
            raise ValueError(
                f"ceremony_id must be a BacklogReviewCeremonyId, got {type(self.ceremony_id)}"
            )

        if not isinstance(self.story_id, StoryId):
            raise ValueError(
                f"story_id must be a StoryId, got {type(self.story_id)}"
            )

    def __str__(self) -> str:
        """String representation for logging."""
        return (
            f"BacklogReviewResult(ceremony={self.ceremony_id.value}, "
            f"story={self.story_id.value}, "
            f"agent_id={self.agent_id}, "
            f"role={self.role.value}, "
            f"reviewed_at={self.reviewed_at.isoformat()})"
        )
