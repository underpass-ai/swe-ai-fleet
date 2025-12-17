"""Use case to retrieve task decision metadata.

Following DDD + Hexagonal Architecture:
- Use case receives Port (interface) via DI
- Use case orchestrates domain logic
- Returns domain value object (not infrastructure concerns)
"""

import logging

from core.context.domain.task_decision_metadata import TaskDecisionMetadata
from core.context.ports.task_decision_metadata_query_port import TaskDecisionMetadataQueryPort

logger = logging.getLogger(__name__)


class GetTaskDecisionMetadataUseCase:
    """Use case to retrieve decision metadata for a specific task.

    This use case retrieves the WHY behind a task's existence - the decision
    context from Planning Service's FASE 1+2 (Backlog Review Ceremony) where
    technical councils (ARCHITECT, QA, DEVOPS) selected this task.

    Following Hexagonal Architecture:
    - Receives TaskDecisionMetadataQueryPort (interface) via DI
    - Orchestrates query execution and validation
    - Returns domain value objects (NO infrastructure concerns)
    """

    def __init__(self, query_port: TaskDecisionMetadataQueryPort) -> None:
        """Initialize use case with dependency injection via Port.

        Args:
            query_port: Port for querying decision metadata (interface, not implementation)
        """
        self._query_port = query_port

    async def execute(self, task_id: str) -> TaskDecisionMetadata | None:
        """Execute task decision metadata retrieval.

        Args:
            task_id: Unique identifier of the task

        Returns:
            TaskDecisionMetadata if found, None if task has no decision metadata

        Raises:
            ValueError: If task_id is invalid (fail-fast)
            Exception: If query execution fails (propagated from adapter)
        """
        # Validate inputs (fail-fast)
        if not task_id or not task_id.strip():
            raise ValueError("task_id is required and cannot be empty")

        logger.debug(f"Retrieving decision metadata for task: {task_id}")

        # Query via Port (hexagonal boundary)
        metadata = await self._query_port.get_task_decision_metadata(task_id)

        if metadata:
            logger.info(
                f"✓ Decision metadata found for task {task_id}: "
                f"decided_by={metadata.decided_by}, source={metadata.source}"
            )
        else:
            logger.debug(
                f"No decision metadata found for task {task_id} "
                "(task may not have semantic relationships from Planning Service)"
            )

        return metadata

