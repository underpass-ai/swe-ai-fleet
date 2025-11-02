"""Story State value object (FSM states)."""

from dataclasses import dataclass
from enum import Enum


class StoryStateEnum(str, Enum):
    """
    FSM States for a Story lifecycle.

    State Machine:
    DRAFT → PO_REVIEW → READY_FOR_PLANNING → PLANNED → READY_FOR_EXECUTION →
    IN_PROGRESS → CODE_REVIEW → TESTING → READY_TO_REVIEW → ACCEPTED → DONE → ARCHIVED

    Sprint Closure Handling:
    - ACCEPTED → DONE (normal flow when sprint ends)
    - IN_PROGRESS/CODE_REVIEW/TESTING/READY_TO_REVIEW → CARRY_OVER (sprint ended, incomplete)
    - CARRY_OVER → DRAFT (PO reevaluates and re-estimates)
    - CARRY_OVER → READY_FOR_EXECUTION (continue in next sprint)
    - CARRY_OVER → ARCHIVED (PO decides to cancel)

    Key States:
    - READY_FOR_PLANNING: PO approved scope, ready for task derivation
    - PLANNED: Tasks derived, ready to be picked up
    - READY_FOR_EXECUTION: Queued for execution, waiting for agent pickup
    - IN_PROGRESS: Agent actively executing
    - CODE_REVIEW: Technical code review by architect/peer agents
    - TESTING: Automated testing phase
    - READY_TO_REVIEW: Tests passed, awaiting final PO/QA examination
    - ACCEPTED: PO/QA accepted the work (story functionally complete)
    - CARRY_OVER: Sprint ended with story incomplete, needs reevaluation
    - DONE: Sprint/agile cycle finished (formal closure)

    Alternative flows:
    - Any state → DRAFT (reset)
    - CODE_REVIEW → IN_PROGRESS (review rejected, rework)
    - TESTING → IN_PROGRESS (tests failed, rework)
    - READY_TO_REVIEW → IN_PROGRESS (PO/QA rejected, rework)
    """

    DRAFT = "DRAFT"
    PO_REVIEW = "PO_REVIEW"
    READY_FOR_PLANNING = "READY_FOR_PLANNING"
    PLANNED = "PLANNED"
    READY_FOR_EXECUTION = "READY_FOR_EXECUTION"
    IN_PROGRESS = "IN_PROGRESS"
    CODE_REVIEW = "CODE_REVIEW"
    TESTING = "TESTING"
    READY_TO_REVIEW = "READY_TO_REVIEW"
    ACCEPTED = "ACCEPTED"
    CARRY_OVER = "CARRY_OVER"
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

        FSM Transition Rules (Normal Flow):
        - DRAFT → PO_REVIEW
        - PO_REVIEW → READY_FOR_PLANNING (if approved)
        - PO_REVIEW → DRAFT (if rejected)
        - READY_FOR_PLANNING → PLANNED (after task derivation)
        - PLANNED → READY_FOR_EXECUTION (tasks ready, queued for pickup)
        - READY_FOR_EXECUTION → IN_PROGRESS (agent picks up execution)
        - IN_PROGRESS → CODE_REVIEW (work complete, start technical review)
        - CODE_REVIEW → TESTING (code review passed)
        - CODE_REVIEW → IN_PROGRESS (code review rejected, rework)
        - TESTING → READY_TO_REVIEW (tests passed, awaiting final PO/QA examination)
        - TESTING → IN_PROGRESS (tests failed, rework)
        - READY_TO_REVIEW → ACCEPTED (PO/QA accepted the work)
        - READY_TO_REVIEW → IN_PROGRESS (PO/QA rejected, rework)
        - ACCEPTED → DONE (sprint/agile cycle finished)
        - DONE → ARCHIVED

        Sprint Closure Transitions:
        - READY_FOR_EXECUTION → CARRY_OVER (sprint ended, queued but not picked up)
        - IN_PROGRESS → CARRY_OVER (sprint ended during execution)
        - CODE_REVIEW → CARRY_OVER (sprint ended during review)
        - TESTING → CARRY_OVER (sprint ended during testing)
        - READY_TO_REVIEW → CARRY_OVER (sprint ended before final acceptance)

        Carry-Over Resolution:
        - CARRY_OVER → DRAFT (PO reevaluates and re-estimates)
        - CARRY_OVER → READY_FOR_EXECUTION (continue in next sprint)
        - CARRY_OVER → ARCHIVED (PO cancels story)

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
            StoryStateEnum.READY_FOR_PLANNING: {StoryStateEnum.PLANNED},
            StoryStateEnum.PLANNED: {StoryStateEnum.READY_FOR_EXECUTION},
            StoryStateEnum.READY_FOR_EXECUTION: {
                StoryStateEnum.IN_PROGRESS,
                StoryStateEnum.CARRY_OVER,  # Sprint closure (queued but not picked up)
            },
            StoryStateEnum.IN_PROGRESS: {
                StoryStateEnum.CODE_REVIEW,
                StoryStateEnum.CARRY_OVER,  # Sprint closure
            },
            StoryStateEnum.CODE_REVIEW: {
                StoryStateEnum.TESTING,
                StoryStateEnum.IN_PROGRESS,
                StoryStateEnum.CARRY_OVER,  # Sprint closure
            },
            StoryStateEnum.TESTING: {
                StoryStateEnum.READY_TO_REVIEW,
                StoryStateEnum.IN_PROGRESS,
                StoryStateEnum.CARRY_OVER,  # Sprint closure
            },
            StoryStateEnum.READY_TO_REVIEW: {
                StoryStateEnum.ACCEPTED,
                StoryStateEnum.IN_PROGRESS,
                StoryStateEnum.CARRY_OVER,  # Sprint closure
            },
            StoryStateEnum.ACCEPTED: {StoryStateEnum.DONE},
            StoryStateEnum.CARRY_OVER: {
                StoryStateEnum.DRAFT,  # Reevaluate and re-estimate
                StoryStateEnum.READY_FOR_EXECUTION,  # Continue in next sprint
                StoryStateEnum.ARCHIVED,  # Cancel story
            },
            StoryStateEnum.DONE: {StoryStateEnum.ARCHIVED},
            StoryStateEnum.ARCHIVED: set(),  # Terminal state
        }

        allowed_states = valid_transitions.get(self.value, set())
        return target_state.value in allowed_states

    def __str__(self) -> str:
        """String representation for logging."""
        return self.value.value

