"""StoryReviewResultDTO - Input DTO for processing story review results.

Application Layer DTO:
- Encapsulates story review result data from Orchestrator
- Used as input to ProcessStoryReviewResultUseCase
- NO serialization methods (mappers handle conversion)

Following DDD + Hexagonal Architecture:
- DTO lives in application layer
- Immutable with validation
- No to_dict() / from_dict() methods
"""

from dataclasses import dataclass
from datetime import datetime

from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.statuses.backlog_review_role import (
    BacklogReviewRole,
)


@dataclass(frozen=True)
class StoryReviewResultDTO:
    """
    DTO for story review result data.

    Encapsulates data received from Orchestrator via NATS events.

    Attributes:
        ceremony_id: ID of the ceremony
        story_id: Story that was reviewed
        role: Council role (BacklogReviewRole enum)
        feedback: Council feedback/proposal text
        reviewed_at: Timestamp when review was completed
    """

    ceremony_id: BacklogReviewCeremonyId
    story_id: StoryId
    role: BacklogReviewRole
    feedback: str
    reviewed_at: datetime

    def __post_init__(self) -> None:
        """Validate DTO (fail-fast).

        Raises:
            ValueError: If validation fails
        """
        if not isinstance(self.role, BacklogReviewRole):
            raise ValueError(
                f"role must be a BacklogReviewRole enum, got {type(self.role)}"
            )

        if not self.feedback or not self.feedback.strip():
            raise ValueError("feedback cannot be empty")

