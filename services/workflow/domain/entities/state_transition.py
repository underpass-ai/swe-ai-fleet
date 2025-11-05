"""State transition entity.

Records a single workflow state transition for audit trail.
Following DDD and Hexagonal Architecture.
"""

from dataclasses import dataclass
from datetime import datetime

from core.agents_and_tools.agents.domain.entities.rbac.action import ActionEnum
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
    """
    
    from_state: str
    to_state: str
    action: ActionEnum
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
        rejection_actions = (
            ActionEnum.REJECT_DESIGN,
            ActionEnum.REJECT_TESTS,
            ActionEnum.REJECT_STORY,
        )
        if self.action in rejection_actions:
            if not self.feedback or len(self.feedback.strip()) < 10:
                raise ValueError(
                    f"Action {self.action.name} requires substantial feedback (min 10 chars)"
                )
    
    def is_rejection(self) -> bool:
        """Check if this transition represents a rejection."""
        return self.action in (
            ActionEnum.REJECT_DESIGN,
            ActionEnum.REJECT_TESTS,
            ActionEnum.REJECT_STORY,
        )
    
    def is_approval(self) -> bool:
        """Check if this transition represents an approval."""
        return self.action in (
            ActionEnum.APPROVE_DESIGN,
            ActionEnum.APPROVE_TESTS,
            ActionEnum.APPROVE_STORY,
        )
    
    def is_system_action(self) -> bool:
        """Check if this was a system-initiated transition."""
        return self.actor_role.is_system()

