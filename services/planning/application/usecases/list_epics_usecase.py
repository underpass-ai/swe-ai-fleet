"""Use case to list epics."""

import logging

from planning.application.ports.storage_port import StoragePort
from planning.domain.entities.epic import Epic
from planning.domain.value_objects.identifiers.project_id import ProjectId

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
        epics_result = await self._storage.list_epics(
            project_id=project_id,
            limit=limit,
            offset=offset,
        )

        if epics_result in (None, Ellipsis):
            logger.warning(
                "Storage adapter returned %s for list_epics; defaulting to []",
                type(epics_result).__name__,
            )
            return []

        try:
            epics = list(epics_result)
        except TypeError:
            logger.warning(
                "Storage adapter returned non-iterable %s; defaulting to []",
                type(epics_result).__name__,
            )
            return []

        logger.info(f"✓ Found {len(epics)} epics")
        return epics

