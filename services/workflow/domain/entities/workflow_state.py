"""Workflow state entity.

Represents the current state of a task in the workflow.
Following DDD and Hexagonal Architecture.
"""

from dataclasses import dataclass
from datetime import datetime

from core.shared.domain import Action, ActionEnum

from services.workflow.domain.entities.state_transition import StateTransition
from services.workflow.domain.value_objects.role import NO_ROLE, Role
from services.workflow.domain.value_objects.story_id import StoryId
from services.workflow.domain.value_objects.task_id import TaskId
from services.workflow.domain.value_objects.workflow_state_enum import WorkflowStateEnum


@dataclass(frozen=True)
class WorkflowState:
    """Current workflow state for a task.

    Aggregate root for workflow domain.
    Tracks task through multi-role validation workflow.

    Following DDD principles:
    - Immutable (frozen=True)
    - Encapsulates workflow business logic
    - History as immutable tuple (audit trail)
    - Fail-fast validation
    - No reflection or dynamic mutation

    Granularity: TASK level (not step level).
    Steps are ephemeral and not persisted.
    """

    task_id: TaskId
    story_id: StoryId
    current_state: WorkflowStateEnum
    role_in_charge: Role | None  # Who should act now (Role value object)
    required_action: Action | None  # What action is needed (Action value object)
    history: tuple[StateTransition, ...]  # Audit trail (immutable)
    feedback: str | None  # Feedback from validator if rejected
    updated_at: datetime
    retry_count: int = 0

    def __post_init__(self) -> None:
        """Validate business invariants (fail-fast).

        Type validation is handled by type hints.
        Only validate business rules here.
        """
        # Business rule: retry count cannot be negative
        if self.retry_count < 0:
            raise ValueError(f"retry_count cannot be negative, got {self.retry_count}")

    @staticmethod
    def create_initial(task_id: TaskId, story_id: StoryId) -> "WorkflowState":
        """Factory method: Create initial workflow state for a task.

        Initial state when story transitions to READY_FOR_EXECUTION:
        - current_state: TODO (task not started yet)
        - role_in_charge: developer (who should claim it)
        - required_action: CLAIM_TASK
        - no history (empty tuple)
        - no feedback
        - retry_count: 0

        Following DDD factory pattern:
        - Domain entity knows how to create itself
        - Encapsulates initial state logic
        - Type-safe (returns WorkflowState, not dict)

        Args:
            task_id: Task identifier
            story_id: Parent story identifier

        Returns:
            WorkflowState with initial configuration
        """
        return WorkflowState(
            task_id=task_id,
            story_id=story_id,
            current_state=WorkflowStateEnum.TODO,
            role_in_charge=Role("developer"),
            required_action=Action(value=ActionEnum.CLAIM_TASK),
            history=tuple(),  # Empty history (no transitions yet)
            feedback=None,
            updated_at=datetime.now(),
            retry_count=0,
        )

    def is_terminal(self) -> bool:
        """Check if workflow has reached a terminal state."""
        return self.current_state.is_terminal()

    def is_waiting_for_action(self) -> bool:
        """Check if workflow is waiting for someone to act."""
        return self.current_state.is_waiting_for_role()

    def needs_role(self, role: Role) -> bool:
        """Check if this task needs a specific role to act."""
        return self.role_in_charge == role

    def is_ready_for_role(self, role: Role) -> bool:
        """Check if this task is ready for a specific role to act on.

        Tell, Don't Ask: Encapsulates business logic for task readiness.
        Combines waiting state + role assignment in single domain method.

        Args:
            role: Role to check readiness for

        Returns:
            True if task is waiting AND assigned to this role
        """
        return self.is_waiting_for_action() and self.needs_role(role)

    def should_notify_role_assignment(self) -> bool:
        """Check if this task should trigger role assignment notification.

        Tell, Don't Ask principle: Encapsulate business logic in domain.

        Returns:
            True if task is ready for role assignment
        """
        return self.is_waiting_for_action() and self.role_in_charge is not None

    def should_notify_validation_required(self) -> bool:
        """Check if this task should trigger validation notification.

        Tell, Don't Ask principle: Encapsulate business logic in domain.
        Reuses is_waiting_for_action() instead of asking current_state directly.

        Returns:
            True if validators should be notified
        """
        return self.is_waiting_for_action() and self.role_in_charge is not None

    def get_current_state_value(self) -> str:
        """Get current state as string value.

        Tell, Don't Ask: Encapsulate attribute access.
        Instead of: workflow_state.current_state.value
        Use: workflow_state.get_current_state_value()

        Returns:
            Current state string (e.g., "implementing", "pending_arch_review")
        """
        return self.current_state.value

    def get_required_action_value(self) -> str:
        """Get required action as string value.

        Tell, Don't Ask: Encapsulate attribute access.
        Instead of: workflow_state.required_action.value.value or ""
        Use: workflow_state.get_required_action_value()

        Returns:
            Required action string (e.g., "claim_task", "approve_design")
            or ActionEnum.NO_ACTION if no action required
        """
        if self.required_action is None:
            return ActionEnum.NO_ACTION.value
        return self.required_action.get_value()

    def get_role_in_charge_value(self) -> str:
        """Get role in charge as string value.

        Tell, Don't Ask: Encapsulate attribute access.
        Instead of: str(workflow_state.role_in_charge) or ""
        Use: workflow_state.get_role_in_charge_value()

        Returns:
            Role string (e.g., "developer", "architect", "qa", "po")
            or NO_ROLE sentinel value if no role assigned
        """
        if self.role_in_charge is None:
            return NO_ROLE
        return str(self.role_in_charge)

    def get_last_transition(self) -> StateTransition | None:
        """Get the most recent state transition."""
        return self.history[-1] if self.history else None

    def has_been_rejected(self) -> bool:
        """Check if this task has been rejected at any point."""
        return any(t.is_rejection() for t in self.history)

    def get_rejection_count(self) -> int:
        """Count how many times this task was rejected."""
        return sum(1 for t in self.history if t.is_rejection())

    def with_new_state(
        self,
        new_state: WorkflowStateEnum,
        new_role: Role | None,
        new_action: Action | None,
        transition: StateTransition,
        new_feedback: str | None = None,
    ) -> "WorkflowState":
        """Create new WorkflowState with updated state (immutable).

        Returns a new instance with the transition applied.
        Used by WorkflowStateMachine to execute transitions.

        Args:
            new_state: The new workflow state
            new_role: Role that should act next (None if terminal/auto)
            new_action: Action required next (None if terminal/auto)
            transition: StateTransition to add to history
            new_feedback: Updated feedback (or None to preserve current)

        Returns:
            New WorkflowState instance
        """
        return WorkflowState(
            task_id=self.task_id,
            story_id=self.story_id,
            current_state=new_state,
            role_in_charge=new_role,
            required_action=new_action,
            history=self.history + (transition,),
            feedback=new_feedback if new_feedback is not None else self.feedback,
            updated_at=transition.timestamp,
            retry_count=self.retry_count,
        )

    def with_retry(self, retry_timestamp: datetime) -> "WorkflowState":
        """Create new WorkflowState for retry (immutable).

        Resets to initial state for complete retry.
        Preserves history for audit trail.

        Returns:
            New WorkflowState instance reset to TODO
        """
        retry_transition = StateTransition(
            from_state=self.current_state.value,
            to_state=WorkflowStateEnum.TODO.value,
            action=Action(value=ActionEnum.RETRY),
            actor_role=Role.system(),
            timestamp=retry_timestamp,
            feedback=f"Retry #{self.retry_count + 1} - Reset to initial state",
        )

        return WorkflowState(
            task_id=self.task_id,
            story_id=self.story_id,
            current_state=WorkflowStateEnum.TODO,
            role_in_charge=None,
            required_action=None,
            history=self.history + (retry_transition,),
            feedback=None,  # Clear feedback for fresh start
            updated_at=retry_timestamp,
            retry_count=self.retry_count + 1,
        )

