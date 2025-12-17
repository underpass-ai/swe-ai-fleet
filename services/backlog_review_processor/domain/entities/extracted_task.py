"""ExtractedTask domain entity."""

from dataclasses import dataclass

from backlog_review_processor.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from backlog_review_processor.domain.value_objects.identifiers.story_id import StoryId


@dataclass(frozen=True)
class ExtractedTask:
    """
    Domain Entity: Task extracted from LLM response.

    Represents a task extracted from the agent's task extraction response,
    including all metadata needed to create it in Planning Service.

    Attributes:
        story_id: Story identifier
        ceremony_id: Ceremony identifier
        title: Task title
        description: Task description
        estimated_hours: Estimated hours for the task
        deliberation_indices: List of indices into ceremony's agent_deliberations
    """

    story_id: StoryId
    ceremony_id: BacklogReviewCeremonyId
    title: str
    description: str
    estimated_hours: int
    deliberation_indices: list[int]

    def __post_init__(self) -> None:
        """Validate domain entity (fail-fast).

        Raises:
            ValueError: If validation fails
        """
        if not self.title or not self.title.strip():
            raise ValueError("title cannot be empty")

        if not isinstance(self.story_id, StoryId):
            raise ValueError(
                f"story_id must be a StoryId, got {type(self.story_id)}"
            )

        if not isinstance(self.ceremony_id, BacklogReviewCeremonyId):
            raise ValueError(
                f"ceremony_id must be a BacklogReviewCeremonyId, got {type(self.ceremony_id)}"
            )

        if self.estimated_hours < 0:
            raise ValueError(
                f"estimated_hours must be non-negative, got {self.estimated_hours}"
            )

        if not isinstance(self.deliberation_indices, list):
            raise ValueError(
                f"deliberation_indices must be a list, got {type(self.deliberation_indices)}"
            )

    def __str__(self) -> str:
        """String representation for logging."""
        return (
            f"ExtractedTask(title={self.title}, "
            f"story={self.story_id.value}, "
            f"ceremony={self.ceremony_id.value}, "
            f"estimated_hours={self.estimated_hours}, "
            f"deliberation_count={len(self.deliberation_indices)})"
        )
