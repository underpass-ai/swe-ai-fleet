"""AddStoriesToReviewUseCase - Add stories to ceremony.

Use Case (Application Layer):
- Add stories to an existing ceremony
- Validates ceremony state
- Updates ceremony entity
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from planning.application.ports import StoragePort
from planning.domain.entities.backlog_review_ceremony import BacklogReviewCeremony
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.story_id import StoryId

logger = logging.getLogger(__name__)


class CeremonyNotFoundError(Exception):
    """Exception raised when ceremony is not found."""

    pass


@dataclass
class AddStoriesToReviewUseCase:
    """
    Add stories to an existing backlog review ceremony.

    This use case:
    1. Retrieves ceremony from storage
    2. Validates ceremony exists and is not completed/cancelled
    3. Adds each story to ceremony (using immutable add_story method)
    4. Persists updated ceremony
    5. Returns updated ceremony

    Following Hexagonal Architecture:
    - Depends on StoragePort only
    - Returns domain entity
    - No infrastructure dependencies
    """

    storage: StoragePort

    async def execute(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        story_ids: tuple[StoryId, ...],
    ) -> BacklogReviewCeremony:
        """
        Add stories to ceremony.

        Args:
            ceremony_id: ID of ceremony to update
            story_ids: Stories to add

        Returns:
            Updated BacklogReviewCeremony entity

        Raises:
            CeremonyNotFoundError: If ceremony not found
            ValueError: If ceremony is completed/cancelled or story already exists
            StorageError: If persistence fails
        """
        # Retrieve ceremony
        ceremony = await self.storage.get_backlog_review_ceremony(ceremony_id)

        if not ceremony:
            raise CeremonyNotFoundError(
                f"Ceremony not found: {ceremony_id.value}"
            )

        # Add each story (immutably)
        updated_at = datetime.now(UTC)
        for story_id in story_ids:
            ceremony = ceremony.add_story(story_id, updated_at)

        # Persist updated ceremony
        await self.storage.save_backlog_review_ceremony(ceremony)

        logger.info(
            f"Added {len(story_ids)} stories to ceremony {ceremony_id.value}"
        )

        return ceremony

