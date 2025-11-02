"""Story State value object (FSM states)."""

from dataclasses import dataclass
from enum import Enum


class StoryStateEnum(str, Enum):
    """
    FSM States for a Story lifecycle.
    
    State Machine:
    DRAFT → PO_REVIEW → READY_FOR_PLANNING → IN_PROGRESS → 
    CODE_REVIEW → TESTING → DONE → ARCHIVED
    
    Alternative flows:
    - Any state → DRAFT (reset)
    - TESTING → IN_PROGRESS (rework)
    """
    
    DRAFT = "DRAFT"
    PO_REVIEW = "PO_REVIEW"
    READY_FOR_PLANNING = "READY_FOR_PLANNING"
    IN_PROGRESS = "IN_PROGRESS"
    CODE_REVIEW = "CODE_REVIEW"
    TESTING = "TESTING"
    DONE = "DONE"
    ARCHIVED = "ARCHIVED"


@dataclass(frozen=True)
class StoryState:
    """
    Value Object: Current state of a Story in FSM.
    
    Domain Invariants:
    - State must be one of the valid StoryStateEnum values
    - State transitions follow FSM rules
    
    Immutability: frozen=True ensures no mutation after creation.
    """
    
    value: StoryStateEnum
    
    def __post_init__(self) -> None:
        """
        Fail-fast validation.
        
        Raises:
            ValueError: If state is not a valid StoryStateEnum.
        """
        if not isinstance(self.value, StoryStateEnum):
            raise ValueError(
                f"Invalid state: {self.value}. Must be StoryStateEnum."
            )
    
    def is_draft(self) -> bool:
        """Check if state is DRAFT."""
        return self.value == StoryStateEnum.DRAFT
    
    def is_done(self) -> bool:
        """Check if state is DONE."""
        return self.value == StoryStateEnum.DONE
    
    def is_in_progress(self) -> bool:
        """Check if state is IN_PROGRESS."""
        return self.value == StoryStateEnum.IN_PROGRESS
    
    def can_transition_to(self, target_state: "StoryState") -> bool:
        """
        Check if transition to target state is valid.
        
        FSM Transition Rules:
        - DRAFT → PO_REVIEW
        - PO_REVIEW → READY_FOR_PLANNING (if approved)
        - PO_REVIEW → DRAFT (if rejected)
        - READY_FOR_PLANNING → IN_PROGRESS
        - IN_PROGRESS → CODE_REVIEW
        - CODE_REVIEW → TESTING
        - CODE_REVIEW → IN_PROGRESS (if rejected)
        - TESTING → DONE
        - TESTING → IN_PROGRESS (if failed)
        - DONE → ARCHIVED
        - Any → DRAFT (reset)
        
        Args:
            target_state: Target state to transition to.
        
        Returns:
            True if transition is valid, False otherwise.
        """
        # Reset to DRAFT is always allowed
        if target_state.value == StoryStateEnum.DRAFT:
            return True
        
        # Valid transitions map
        valid_transitions = {
            StoryStateEnum.DRAFT: {StoryStateEnum.PO_REVIEW},
            StoryStateEnum.PO_REVIEW: {
                StoryStateEnum.READY_FOR_PLANNING,
                StoryStateEnum.DRAFT,
            },
            StoryStateEnum.READY_FOR_PLANNING: {StoryStateEnum.IN_PROGRESS},
            StoryStateEnum.IN_PROGRESS: {StoryStateEnum.CODE_REVIEW},
            StoryStateEnum.CODE_REVIEW: {
                StoryStateEnum.TESTING,
                StoryStateEnum.IN_PROGRESS,
            },
            StoryStateEnum.TESTING: {
                StoryStateEnum.DONE,
                StoryStateEnum.IN_PROGRESS,
            },
            StoryStateEnum.DONE: {StoryStateEnum.ARCHIVED},
            StoryStateEnum.ARCHIVED: set(),  # Terminal state
        }
        
        allowed_states = valid_transitions.get(self.value, set())
        return target_state.value in allowed_states
    
    def __str__(self) -> str:
        """String representation for logging."""
        return self.value.value

