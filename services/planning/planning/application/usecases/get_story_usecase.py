"""Use case to get a story by ID."""

import logging

from planning.application.ports.storage_port import StoragePort
from planning.domain.entities.story import Story
from planning.domain.value_objects.identifiers.story_id import StoryId

logger = logging.getLogger(__name__)


class GetStoryUseCase:
    """Get a story by ID.

    Following Hexagonal Architecture + DDD.
    """

    def __init__(self, storage: StoragePort):
        """Initialize with storage port (DI)."""
        self._storage = storage

    async def execute(self, story_id: StoryId) -> Story | None:
        """Get story by ID.

        Args:
            story_id: StoryId value object

        Returns:
            Story entity or None if not found
        """
        logger.info(
            f"Getting story: {story_id.value}",
            extra={"story_id": story_id.value, "use_case": "GetStory"},
        )

        story = await self._storage.get_story(story_id)

        if story:
            logger.info(f"✓ Story found: {story_id.value}")
        else:
            logger.warning(f"Story not found: {story_id.value}")

        return story

