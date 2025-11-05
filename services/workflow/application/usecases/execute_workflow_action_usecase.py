"""Execute workflow action use case.

Processes agent work completion events and advances workflow.
Following Hexagonal Architecture.
"""

from datetime import datetime

from core.agents_and_tools.agents.domain.entities.rbac.action import Action
from services.workflow.application.ports.messaging_port import MessagingPort
from services.workflow.application.ports.workflow_state_repository_port import (
    WorkflowStateRepositoryPort,
)
from services.workflow.domain.entities.workflow_state import WorkflowState
from services.workflow.domain.exceptions.workflow_transition_error import (
    WorkflowTransitionError,
)
from services.workflow.domain.services.workflow_state_machine import WorkflowStateMachine
from services.workflow.domain.value_objects.artifact_type import ArtifactType
from services.workflow.domain.value_objects.role import Role
from services.workflow.domain.value_objects.task_id import TaskId
from services.workflow.domain.value_objects.workflow_event_type import WorkflowEventType


class ExecuteWorkflowActionUseCase:
    """Use case for executing workflow actions.

    Processes agent.work.completed events:
    1. Load current workflow state
    2. Validate action is allowed
    3. Execute transition via FSM
    4. Persist new state
    5. Publish events (state changed, task assigned, validation required)

    Following Hexagonal Architecture:
    - Depends on ports (interfaces), not concrete implementations
    - Pure business orchestration logic
    - No infrastructure dependencies
    """

    def __init__(
        self,
        repository: WorkflowStateRepositoryPort,
        messaging: MessagingPort,
        state_machine: WorkflowStateMachine,
    ) -> None:
        """Initialize use case with dependencies.

        Args:
            repository: Workflow state persistence port
            messaging: Event publishing port
            state_machine: Workflow FSM domain service
        """
        self._repository = repository
        self._messaging = messaging
        self._state_machine = state_machine

    async def execute(
        self,
        task_id: TaskId,
        action: Action,
        actor_role: Role,
        timestamp: datetime,
        feedback: str | None = None,
    ) -> WorkflowState:
        """Execute a workflow action.

        Use case receives domain objects (NOT primitives).
        Caller (gRPC servicer/NATS consumer) is responsible for conversion.

        Args:
            task_id: Task identifier (value object)
            action: Action to execute (value object)
            actor_role: Role executing the action (value object)
            timestamp: Event timestamp (from NATS message)
            feedback: Optional feedback (required for rejections)

        Returns:
            New WorkflowState after transition

        Raises:
            ValueError: If task not found
            WorkflowTransitionError: If transition violates FSM rules
        """
        # Load current workflow state
        current_state = await self._repository.get_state(task_id)

        if current_state is None:
            raise ValueError(f"Task {task_id} not found in workflow")

        # Check if action is allowed (RBAC enforcement)
        if not self._state_machine.can_execute_action(current_state, action, actor_role):
            raise WorkflowTransitionError(
                f"Action {action.value.value} not allowed for role {actor_role} "
                f"in state {current_state.current_state.value}"
            )

        # Execute transition
        new_state = self._state_machine.execute_transition(
            current_state=current_state,
            action=action,
            actor_role=actor_role,
            feedback=feedback,
            timestamp=timestamp,
        )

        # Persist new state
        await self._repository.save_state(new_state)

        # Publish state changed event
        await self._messaging.publish_state_changed(
            workflow_state=new_state,
            event_type=str(WorkflowEventType.STATE_CHANGED),
        )

        # Tell, Don't Ask: Domain tells us what events to publish
        if new_state.should_notify_role_assignment():
            await self._messaging.publish_task_assigned(
                task_id=str(new_state.task_id),
                story_id=str(new_state.story_id),
                role=str(new_state.role_in_charge),
                action_required=str(new_state.required_action) if new_state.required_action else "",
            )

        if new_state.should_notify_validation_required():
            await self._messaging.publish_validation_required(
                task_id=str(new_state.task_id),
                story_id=str(new_state.story_id),
                validator_role=str(new_state.role_in_charge),
                artifact_type=ArtifactType.from_action(new_state.required_action),
            )

        # Publish task completed if terminal state
        if new_state.is_terminal():
            await self._messaging.publish_task_completed(
                task_id=str(new_state.task_id),
                story_id=str(new_state.story_id),
                final_state=new_state.current_state.value,
            )

        # Return domain entity (NOT dict)
        # Mapping to dict/protobuf is gRPC servicer responsibility
        return new_state

