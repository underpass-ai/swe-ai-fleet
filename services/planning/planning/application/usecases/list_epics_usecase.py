"""Use case to list epics."""

import logging

from planning.application.ports.storage_port import StoragePort
from planning.domain.entities.epic import Epic
from planning.domain.value_objects.project_id import ProjectId

logger = logging.getLogger(__name__)


class ListEpicsUseCase:
    """List epics with optional project filter."""

    def __init__(self, storage: StoragePort):
        self._storage = storage

    async def execute(
        self,
        project_id: ProjectId | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Epic]:
        logger.info(f"Listing epics: project_id={project_id}, limit={limit}")
        epics = await self._storage.list_epics(
            project_id=project_id,
            limit=limit,
            offset=offset,
        )
        logger.info(f"✓ Found {len(epics)} epics")
        return epics

