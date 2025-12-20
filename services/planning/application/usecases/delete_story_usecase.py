"""DeleteStoryUseCase - Delete a story."""

import logging

from planning.application.ports.storage_port import StoragePort
from planning.domain.value_objects.identifiers.story_id import StoryId

logger = logging.getLogger(__name__)


class DeleteStoryUseCase:
    """Delete a story by ID.

    This use case:
    1. Validates story_id is not empty
    2. Deletes story from dual storage (Neo4j + Valkey)

    Following Hexagonal Architecture:
    - Depends on StoragePort only
    - No infrastructure dependencies
    """

    def __init__(self, storage: StoragePort) -> None:
        """Initialize with storage port (DI)."""
        self._storage = storage

    async def execute(self, story_id: StoryId) -> None:
        """Execute story deletion.

        Args:
            story_id: Story ID to delete

        Raises:
            ValueError: If story_id is empty
        """
        if not story_id or not story_id.value:
            raise ValueError("story_id cannot be empty")

        logger.info(f"Deleting story: {story_id.value}")

        await self._storage.delete_story(story_id)

        logger.info(f"Story deleted: {story_id.value}")
