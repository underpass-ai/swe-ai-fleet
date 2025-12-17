"""Storage port for Task Extraction Service.

Port (interface) for persistence of agent deliberations.
Task Extraction Service persists deliberations to enable observability
and allow Planning Service to query them.
"""

from typing import Protocol

from backlog_review_processor.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from backlog_review_processor.domain.value_objects.identifiers.story_id import StoryId
from backlog_review_processor.domain.value_objects.review.agent_deliberation import (
    AgentDeliberation,
)


class StoragePort(Protocol):
    """Port for storing agent deliberations.

    Following Hexagonal Architecture:
    - Port defines interface (application layer)
    - Adapter implements storage calls (infrastructure layer)
    """

    async def save_agent_deliberation(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        story_id: StoryId,
        deliberation: AgentDeliberation,
    ) -> None:
        """Save an agent deliberation to storage.

        Args:
            ceremony_id: Ceremony identifier
            story_id: Story identifier
            deliberation: Agent deliberation to save

        Raises:
            StorageError: If save fails
        """
        ...
