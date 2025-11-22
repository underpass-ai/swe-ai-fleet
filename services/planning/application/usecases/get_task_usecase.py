"""Use case to get a task by ID."""

import logging

from planning.application.ports.storage_port import StoragePort
from planning.domain.entities.task import Task
from planning.domain.value_objects.identifiers.task_id import TaskId

logger = logging.getLogger(__name__)


class GetTaskUseCase:
    """Get a task by ID."""

    def __init__(self, storage: StoragePort):
        self._storage = storage

    async def execute(self, task_id: TaskId) -> Task | None:
        logger.info(f"Getting task: {task_id.value}")
        task = await self._storage.get_task(task_id)
        if task:
            logger.info(f"✓ Task found: {task_id.value}")
        else:
            logger.warning(f"Task not found: {task_id.value}")
        return task

