"""Use case to synchronize Task from Planning Service to Context graph."""

import logging

from core.context.domain.task import Task
from core.context.ports.graph_command_port import GraphCommandPort

logger = logging.getLogger(__name__)


class SynchronizeTaskFromPlanningUseCase:
    """Synchronize a Task from Planning Service to Context graph.

    Bounded Context: Context Service
    Trigger: planning.task.created event from Planning Service

    Following Hexagonal Architecture + DDD.
    """

    def __init__(self, graph_command: GraphCommandPort):
        """Initialize use case with dependency injection via Port."""
        self._graph = graph_command

    async def execute(self, task: Task) -> None:
        """Execute task synchronization.

        Args:
            task: Domain entity to persist
        """
        # Tell, Don't Ask: entity provides its own log context
        log_ctx = task.get_log_context()
        log_ctx["use_case"] = "SynchronizeTaskFromPlanning"

        logger.info(
            f"Synchronizing task: {task.task_id.to_string()} → plan {task.plan_id.to_string()}",
            extra=log_ctx,
        )

        # Persist via Port
        await self._graph.save_task(task)

        logger.info(
            f"✓ Task synchronized: {task.task_id.to_string()}",
            extra=log_ctx,
        )

