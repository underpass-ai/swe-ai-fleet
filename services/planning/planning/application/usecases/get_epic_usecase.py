"""Use case to get an epic by ID."""

import logging

from planning.application.ports.storage_port import StoragePort
from planning.domain.entities.epic import Epic
from planning.domain.value_objects.identifiers.epic_id import EpicId

logger = logging.getLogger(__name__)


class GetEpicUseCase:
    """Get an epic by ID."""

    def __init__(self, storage: StoragePort):
        self._storage = storage

    async def execute(self, epic_id: EpicId) -> Epic | None:
        logger.info(f"Getting epic: {epic_id.value}")
        epic = await self._storage.get_epic(epic_id)
        if epic:
            logger.info(f"✓ Epic found: {epic_id.value}")
        else:
            logger.warning(f"Epic not found: {epic_id.value}")
        return epic

