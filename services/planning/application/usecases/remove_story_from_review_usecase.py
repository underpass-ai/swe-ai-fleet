"""RemoveStoryFromReviewUseCase - Remove story from ceremony.

Use Case (Application Layer):
- Remove a story from an existing ceremony
- Validates ceremony state
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from planning.application.ports import StoragePort
from planning.application.usecases.add_stories_to_review_usecase import (
    CeremonyNotFoundError,
)
from planning.domain.entities.backlog_review_ceremony import BacklogReviewCeremony
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.story_id import StoryId

logger = logging.getLogger(__name__)


@dataclass
class RemoveStoryFromReviewUseCase:
    """
    Remove a story from a backlog review ceremony.

    This use case:
    1. Retrieves ceremony
    2. Validates ceremony exists and is not completed/cancelled
    3. Removes story using immutable remove_story method
    4. Persists updated ceremony
    5. Returns updated ceremony

    Following Hexagonal Architecture:
    - Depends on StoragePort only
    - Returns domain entity
    """

    storage: StoragePort

    async def execute(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        story_id: StoryId,
    ) -> BacklogReviewCeremony:
        """
        Remove story from ceremony.

        Args:
            ceremony_id: ID of ceremony to update
            story_id: Story to remove

        Returns:
            Updated BacklogReviewCeremony entity

        Raises:
            CeremonyNotFoundError: If ceremony not found
            ValueError: If ceremony is completed/cancelled or story not in ceremony
            StorageError: If persistence fails
        """
        # Retrieve ceremony
        ceremony = await self.storage.get_backlog_review_ceremony(ceremony_id)

        if not ceremony:
            raise CeremonyNotFoundError(
                f"Ceremony not found: {ceremony_id.value}"
            )

        # Remove story (immutably)
        updated_at = datetime.now(UTC)
        ceremony = ceremony.remove_story(story_id, updated_at)

        # Persist updated ceremony
        await self.storage.save_backlog_review_ceremony(ceremony)

        logger.info(
            f"Removed story {story_id.value} from ceremony {ceremony_id.value}"
        )

        return ceremony

