"""Get pending tasks use case.

Retrieves tasks waiting for a specific role.
Following Hexagonal Architecture.
"""

from services.workflow.application.ports.workflow_state_repository_port import (
    WorkflowStateRepositoryPort,
)
from services.workflow.domain.collections.workflow_state_collection import (
    WorkflowStateCollection,
)
from services.workflow.domain.entities.workflow_state import WorkflowState
from services.workflow.domain.value_objects.role import Role


class GetPendingTasksUseCase:
    """Use case for retrieving pending tasks by role.

    Used by:
    - Orchestrator: Find tasks ready for agent assignment
    - gRPC API: GetPendingTasks RPC
    - Agents: Discover work available

    Following Hexagonal Architecture:
    - Depends on ports (interfaces), not concrete implementations
    - Query orchestration with business logic filtering
    """

    def __init__(self, repository: WorkflowStateRepositoryPort) -> None:
        """Initialize use case with dependencies.

        Args:
            repository: Workflow state persistence port
        """
        self._repository = repository

    async def execute(self, role: Role, limit: int = 100) -> list[WorkflowState]:
        """Get pending tasks for a role.

        Use case receives domain objects (NOT primitives).
        Caller (gRPC servicer) is responsible for conversion.

        Args:
            role: Role identifier (value object)
            limit: Maximum number of tasks to return

        Returns:
            List of WorkflowState entities sorted by priority
        """
        # Query pending tasks from repository
        states = await self._repository.get_pending_by_role(str(role), limit)

        # Domain collection encapsulates filtering and sorting logic
        # Tell, Don't Ask: Collection tells us the filtered and sorted result
        collection = WorkflowStateCollection(states)
        result = collection.filter_ready_for_role(role).sort_by_priority()

        # Return domain entities (NOT dicts)
        # Mapping to protobuf is gRPC servicer responsibility
        return result.to_list()

