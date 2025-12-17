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

    Encapsulates data received from vLLM via NATS events (agent.response.completed).

    Attributes:
        ceremony_id: ID of the ceremony
        story_id: Story that was reviewed
        role: Council role (BacklogReviewRole enum)
        agent_id: Specific agent identifier (e.g., "agent-architect-001")
        feedback: Council feedback/proposal text
        proposal: Full proposal/deliberation from agent (dict or str)
        reviewed_at: Timestamp when review was completed
    """

    ceremony_id: BacklogReviewCeremonyId
    story_id: StoryId
    role: BacklogReviewRole
    agent_id: str
    feedback: str
    proposal: dict | str  # Full proposal from agent
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

