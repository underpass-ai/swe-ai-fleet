"""Initialize task workflow use case.

Creates initial workflow state for a task when story is ready for execution.
Following DDD + Hexagonal Architecture.
"""

import logging

from services.workflow.application.ports.messaging_port import MessagingPort
from services.workflow.application.ports.workflow_state_repository_port import (
    WorkflowStateRepositoryPort,
)
from services.workflow.domain.entities.workflow_state import WorkflowState
from services.workflow.domain.value_objects.nats_subjects import NatsSubjects
from services.workflow.domain.value_objects.role import Role
from services.workflow.domain.value_objects.story_id import StoryId
from services.workflow.domain.value_objects.task_id import TaskId

logger = logging.getLogger(__name__)


class InitializeTaskWorkflowUseCase:
    """Use case: Initialize workflow for a task.

    Orchestrates:
    1. Create initial WorkflowState (factory method)
    2. Persist to repository (Neo4j + Valkey)
    3. Publish task assignment event (notify Orchestrator)

    Following Hexagonal Architecture:
    - Application layer (business orchestration)
    - Depends on ports (not adapters)
    - No infrastructure code (NATS, Neo4j, etc.)
    - Pure business logic
    """

    def __init__(
        self,
        repository: WorkflowStateRepositoryPort,
        messaging: MessagingPort,
    ) -> None:
        """Initialize use case with dependencies.

        Args:
            repository: Workflow state repository port
            messaging: Messaging port for event publishing
        """
        self._repository = repository
        self._messaging = messaging

    async def execute(self, task_id: TaskId, story_id: StoryId) -> WorkflowState:
        """Initialize workflow state for a task.

        Business logic:
        1. Create initial state (TODO, assigned to developer, requires CLAIM_TASK)
        2. Persist to repository
        3. Publish task assignment event

        Args:
            task_id: Task identifier
            story_id: Parent story identifier

        Returns:
            Created WorkflowState

        Raises:
            ValueError: If task_id or story_id invalid
            Exception: If repository or messaging fails
        """
        logger.info(f"Initializing workflow for task {task_id} (story: {story_id})")

        # Create initial workflow state using domain factory method
        # Default to developer role for new tasks (business rule)
        workflow_state = WorkflowState.create_initial(
            task_id=task_id,
            story_id=story_id,
            initial_role=Role("developer"),
        )

        # Persist to Neo4j + Valkey (via repository port)
        await self._repository.save(workflow_state)

        logger.debug(
            f"Created workflow state: {task_id} → {workflow_state.get_current_state_value()}"
        )

        # Publish task assignment event (Tell, Don't Ask)
        await self._messaging.publish(
            subject=str(NatsSubjects.WORKFLOW_TASK_ASSIGNED),
            payload={
                "task_id": str(task_id),
                "story_id": str(story_id),
                "assigned_to_role": workflow_state.get_role_in_charge_value(),
                "required_action": workflow_state.get_required_action_value(),
                "current_state": workflow_state.get_current_state_value(),
            },
        )

        logger.info(
            f"✅ Workflow initialized: {task_id} → {workflow_state.get_role_in_charge_value()}"
        )

        return workflow_state

