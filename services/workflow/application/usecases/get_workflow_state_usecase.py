"""Get workflow state use case.

Retrieves current workflow state for a task.
Following Hexagonal Architecture.
"""

from services.workflow.application.ports.workflow_state_repository_port import (
    WorkflowStateRepositoryPort,
)
from services.workflow.domain.entities.workflow_state import WorkflowState
from services.workflow.domain.value_objects.task_id import TaskId


class GetWorkflowStateUseCase:
    """Use case for retrieving workflow state.

    Used by:
    - Orchestrator: Before assigning tasks (check if ready)
    - gRPC API: GetWorkflowState RPC
    - Monitoring: Track task progress

    Following Hexagonal Architecture:
    - Depends on ports (interfaces), not concrete implementations
    - Simple query orchestration
    """

    def __init__(self, repository: WorkflowStateRepositoryPort) -> None:
        """Initialize use case with dependencies.

        Args:
            repository: Workflow state persistence port
        """
        self._repository = repository

    async def execute(self, task_id: TaskId) -> WorkflowState | None:
        """Get workflow state for a task.

        Use case receives domain objects (NOT primitives).
        Caller (gRPC servicer) is responsible for conversion.

        Args:
            task_id: Task identifier (value object)

        Returns:
            WorkflowState if found, None otherwise
        """
        return await self._repository.get_state(task_id)

