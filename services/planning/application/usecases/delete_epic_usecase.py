"""DeleteEpicUseCase - Delete an epic."""

import logging

from planning.application.ports.storage_port import StoragePort
from planning.domain.value_objects.identifiers.epic_id import EpicId

logger = logging.getLogger(__name__)


class DeleteEpicUseCase:
    """Delete an epic by ID.

    This use case:
    1. Validates epic_id is not empty
    2. Deletes epic from dual storage (Neo4j + Valkey)

    Following Hexagonal Architecture:
    - Depends on StoragePort only
    - No infrastructure dependencies
    """

    def __init__(self, storage: StoragePort) -> None:
        """Initialize with storage port (DI)."""
        self._storage = storage

    async def execute(self, epic_id: EpicId) -> None:
        """Execute epic deletion.

        Args:
            epic_id: Epic ID to delete

        Raises:
            ValueError: If epic_id is empty
        """
        if not epic_id or not epic_id.value:
            raise ValueError("epic_id cannot be empty")

        logger.info(f"Deleting epic: {epic_id.value}")

        await self._storage.delete_epic(epic_id)

        logger.info(f"Epic deleted: {epic_id.value}")
