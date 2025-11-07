"""Workflow State Machine (Domain Service).

Orchestrates workflow state transitions following FSM rules.
Following Domain-Driven Design and Hexagonal Architecture.
"""

from datetime import datetime

from core.shared.domain import Action, ActionEnum

from services.workflow.domain.entities.state_transition import StateTransition
from services.workflow.domain.entities.workflow_state import WorkflowState
from services.workflow.domain.exceptions.workflow_transition_error import (
    WorkflowTransitionError,
)
from services.workflow.domain.services.workflow_state_metadata import WorkflowStateMetadata
from services.workflow.domain.services.workflow_transition_rules import (
    WorkflowTransitionRules,
)
from services.workflow.domain.value_objects.role import Role


class WorkflowStateMachine:
    """Domain service for workflow state machine.

    Encapsulates workflow transition logic:
    - Validates transitions against FSM rules
    - Executes transitions (creates new WorkflowState)
    - Handles auto-transitions
    - Enforces RBAC at workflow level

    Following DDD:
    - Domain service (stateless business logic)
    - No infrastructure dependencies
    - Fail-fast validation
    """

    def __init__(self, rules: WorkflowTransitionRules) -> None:
        """Initialize state machine with transition rules.

        Args:
            rules: Workflow transition rules (FSM configuration)
        """
        self._rules = rules

    def can_execute_action(
        self,
        workflow_state: WorkflowState,
        action: Action,
        actor_role: Role,
    ) -> bool:
        """Check if an action can be executed by a role.

        Args:
            workflow_state: Current workflow state
            action: Action to execute (value object)
            actor_role: Role attempting the action (value object)

        Returns:
            True if action is allowed
        """
        return self._rules.can_transition(
            from_state=workflow_state.current_state,
            action=action.value,  # Extract enum for FSM rules
            role=str(actor_role),
        )

    def execute_transition(
        self,
        workflow_state: WorkflowState,
        action: Action,
        actor_role: Role,
        feedback: str | None = None,
        timestamp: datetime | None = None,
    ) -> WorkflowState:
        """Execute a workflow transition.

        Creates a new WorkflowState with the transition applied.
        Enforces FSM rules and RBAC.

        Args:
            workflow_state: Current workflow state
            action: Action to execute (value object)
            actor_role: Role executing the action (value object)
            feedback: Optional feedback (required for rejections)
            timestamp: Timestamp (defaults to now)

        Returns:
            New WorkflowState with transition applied

        Raises:
            WorkflowTransitionError: If transition is not allowed
        """
        if timestamp is None:
            timestamp = datetime.now()

        # Check if transition is allowed
        if not self.can_execute_action(workflow_state, action, actor_role):
            raise WorkflowTransitionError(
                f"Transition from {workflow_state.get_current_state_value()} "
                f"with action {action.get_value()} not allowed for role {actor_role}"
            )

        # Get next state from rules
        next_state_enum = self._rules.get_next_state(
            from_state=workflow_state.current_state,
            action=action.value,  # Extract enum for FSM rules
        )

        if next_state_enum is None:
            raise WorkflowTransitionError(
                f"No transition defined from {workflow_state.get_current_state_value()} "
                f"with action {action.get_value()}"
            )

        # Create state transition record (Tell, Don't Ask)
        transition = StateTransition(
            from_state=workflow_state.get_current_state_value(),
            to_state=next_state_enum.value,
            action=action,
            actor_role=actor_role,
            timestamp=timestamp,
            feedback=feedback,
        )

        # Determine next role and action (domain metadata service)
        next_role = WorkflowStateMetadata.get_responsible_role(next_state_enum)
        next_action = WorkflowStateMetadata.get_expected_action(next_state_enum)

        # Create new workflow state
        new_state = workflow_state.with_new_state(
            new_state=next_state_enum,
            new_role=next_role,
            new_action=next_action,
            transition=transition,
            new_feedback=feedback if transition.is_rejection() else None,
        )

        # Handle auto-transitions (if next state has one)
        if self._rules.is_auto_transition_state(next_state_enum):
            new_state = self._apply_auto_transition(new_state, timestamp)

        return new_state

    def _apply_auto_transition(
        self,
        workflow_state: WorkflowState,
        timestamp: datetime,
    ) -> WorkflowState:
        """Apply auto-transition (system-initiated).

        Args:
            workflow_state: Current workflow state
            timestamp: Timestamp for transition

        Returns:
            New WorkflowState after auto-transition

        Raises:
            ValueError: If state marked as auto-transition but no target defined (configuration error)
        """
        target_state_enum = self._rules.get_auto_transition_target(
            workflow_state.current_state
        )

        if target_state_enum is None:
            # Configuration error: State marked as auto-transition but no target defined
            # Fail-fast instead of silently returning (hidden bugs)
            raise ValueError(
                f"Configuration error: State {workflow_state.get_current_state_value()} "
                f"is marked as auto-transition but no target state defined in FSM config"
            )

        # Create system transition (Tell, Don't Ask)
        transition = StateTransition(
            from_state=workflow_state.get_current_state_value(),
            to_state=target_state_enum.value,
            action=Action(value=ActionEnum.REQUEST_REVIEW),  # Auto-transitions
            actor_role=Role.system(),
            timestamp=timestamp,
            feedback=None,
        )

        # Determine next role and action (domain metadata service)
        next_role = WorkflowStateMetadata.get_responsible_role(target_state_enum)
        next_action = WorkflowStateMetadata.get_expected_action(target_state_enum)

        # Create new workflow state
        new_state = workflow_state.with_new_state(
            new_state=target_state_enum,
            new_role=next_role,
            new_action=next_action,
            transition=transition,
            new_feedback=None,
        )

        # Recursively handle chained auto-transitions
        if self._rules.is_auto_transition_state(target_state_enum):
            new_state = self._apply_auto_transition(new_state, timestamp)

        return new_state


    def get_allowed_actions_for_role(
        self,
        workflow_state: WorkflowState,
        role: str,
    ) -> list[Action]:
        """Get allowed actions for a role in current state.

        Args:
            workflow_state: Current workflow state
            role: Role to check

        Returns:
            List of allowed actions (Action value objects)
        """
        action_enums = self._rules.get_allowed_actions(
            from_state=workflow_state.current_state,
            role=role,
        )

        # Convert ActionEnum list to Action value objects
        return [Action(value=action_enum) for action_enum in action_enums]

    def is_role_responsible(
        self,
        workflow_state: WorkflowState,
        role: str,
    ) -> bool:
        """Check if a role is responsible for current state.

        Args:
            workflow_state: Current workflow state
            role: Role to check

        Returns:
            True if role is responsible
        """
        return workflow_state.needs_role(role)

