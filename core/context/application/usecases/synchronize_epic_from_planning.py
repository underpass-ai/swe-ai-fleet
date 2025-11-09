"""Use case to synchronize Epic from Planning Service to Context graph."""

import logging

from core.context.domain.epic import Epic
from core.context.ports.graph_command_port import GraphCommandPort

logger = logging.getLogger(__name__)


class SynchronizeEpicFromPlanningUseCase:
    """Synchronize an Epic from Planning Service to Context graph.

    Bounded Context: Context Service
    Trigger: planning.epic.created event from Planning Service

    Following Hexagonal Architecture + DDD.
    """

    def __init__(self, graph_command: GraphCommandPort):
        """Initialize use case with dependency injection via Port."""
        self._graph = graph_command

    async def execute(self, epic: Epic) -> None:
        """Execute epic synchronization.

        Args:
            epic: Domain entity to persist
        """
        # Tell, Don't Ask: entity provides its own log context
        log_ctx = epic.get_log_context()
        log_ctx["use_case"] = "SynchronizeEpicFromPlanning"

        logger.info(
            f"Synchronizing epic: {epic.epic_id.to_string()} → project {epic.project_id.to_string()}",
            extra=log_ctx,
        )

        # Persist via Port
        await self._graph.save_epic(epic)

        logger.info(
            f"✓ Epic synchronized: {epic.epic_id.to_string()}",
            extra=log_ctx,
        )

