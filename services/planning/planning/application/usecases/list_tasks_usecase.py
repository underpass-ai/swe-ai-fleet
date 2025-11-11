"""Use case to list tasks."""

import logging

from planning.application.ports.storage_port import StoragePort
from planning.domain.entities.task import Task
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.story_id import StoryId

logger = logging.getLogger(__name__)


class ListTasksUseCase:
    """List tasks with optional story/plan filter."""

    def __init__(self, storage: StoragePort):
        self._storage = storage

    async def execute(
        self,
        story_id: StoryId | None = None,
        plan_id: PlanId | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Task]:
        logger.info(f"Listing tasks: story_id={story_id}, plan_id={plan_id}")
        tasks = await self._storage.list_tasks(
            story_id=story_id,
            plan_id=plan_id,
            limit=limit,
            offset=offset,
        )
        logger.info(f"✓ Found {len(tasks)} tasks")
        return tasks

