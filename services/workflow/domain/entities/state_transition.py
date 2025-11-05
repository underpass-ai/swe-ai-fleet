"""State transition entity.

Records a single workflow state transition for audit trail.
Following DDD and Hexagonal Architecture.
"""

from dataclasses import dataclass
from datetime import datetime

from core.agents_and_tools.agents.domain.entities.rbac.action import Action
from services.workflow.domain.value_objects.role import Role


@dataclass(frozen=True)
class StateTransition:
    """Records a workflow state transition (audit trail).

    Immutable entity that captures WHO did WHAT and WHEN.
    Used for audit trail and workflow history.

    Following DDD principles:
    - Immutable (frozen=True)
    - Fail-fast validation
    - No reflection or dynamic mutation
    - Uses Action value object (not ActionEnum primitive)
    """

    from_state: str
    to_state: str
    action: Action  # Action value object (provides is_rejection(), is_approval(), etc.)
    actor_role: Role  # Role value object
    timestamp: datetime
    feedback: str | None = None

    def __post_init__(self) -> None:
        """Validate business invariants (fail-fast).

        Type validation is handled by type hints.
        Only validate business rules here.
        """
        # Business rule: state names cannot be empty
        if not self.from_state:
            raise ValueError("from_state cannot be empty")

        if not self.to_state:
            raise ValueError("to_state cannot be empty")

        # Business rule: rejections require substantial feedback (min 10 chars)
        # Tell, Don't Ask: Action knows if it's a rejection
        if self.action.is_rejection():
            if not self.feedback or len(self.feedback.strip()) < 10:
                raise ValueError(
                    f"Rejection action requires substantial feedback (min 10 chars)"
                )

    def is_rejection(self) -> bool:
        """Check if this transition represents a rejection.

        Tell, Don't Ask: Delegates to Action value object.
        """
        return self.action.is_rejection()

    def is_approval(self) -> bool:
        """Check if this transition represents an approval.

        Tell, Don't Ask: Delegates to Action value object.
        """
        return self.action.is_approval()

    def is_system_action(self) -> bool:
        """Check if this was a system-initiated transition."""
        return self.actor_role.is_system()

