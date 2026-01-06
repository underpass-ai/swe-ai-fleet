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

    async def get_agent_deliberations(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        story_id: StoryId,
    ) -> list[AgentDeliberation]:
        """Get all agent deliberations for a ceremony and story.

        Args:
            ceremony_id: Ceremony identifier
            story_id: Story identifier

        Returns:
            List of AgentDeliberation value objects

        Raises:
            StorageError: If query fails
        """
        ...

    async def has_all_role_deliberations(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        story_id: StoryId,
    ) -> bool:
        """Check if all required roles (ARCHITECT, QA, DEVOPS) have deliberations.

        Args:
            ceremony_id: Ceremony identifier
            story_id: Story identifier

        Returns:
            True if all 3 roles have at least one deliberation, False otherwise

        Raises:
            StorageError: If query fails
        """
        ...
