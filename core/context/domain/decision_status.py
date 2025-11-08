"""DecisionStatus enum - Status of a decision in the decision graph."""

from enum import Enum


class DecisionStatus(str, Enum):
    """Status of a decision in the decision-making process.

    Represents the lifecycle state of an architectural or implementation decision.
    """

    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    IMPLEMENTED = "IMPLEMENTED"
    DEPRECATED = "DEPRECATED"

    def is_final(self) -> bool:
        """Check if this status is a terminal state.

        Returns:
            True if decision cannot change from this status
        """
        return self in {
            DecisionStatus.REJECTED,
            DecisionStatus.DEPRECATED,
        }

    def is_active(self) -> bool:
        """Check if this decision is actively being used.

        Returns:
            True if decision is approved or implemented
        """
        return self in {
            DecisionStatus.APPROVED,
            DecisionStatus.IMPLEMENTED,
        }

    def can_transition_to(self, new_status: "DecisionStatus") -> bool:
        """Check if transition to new status is valid.

        Args:
            new_status: Target status

        Returns:
            True if transition is allowed
        """
        # Cannot change from final states
        if self.is_final():
            return False

        # Valid transitions
        transitions = {
            DecisionStatus.PROPOSED: {
                DecisionStatus.APPROVED,
                DecisionStatus.REJECTED,
            },
            DecisionStatus.APPROVED: {
                DecisionStatus.IMPLEMENTED,
                DecisionStatus.DEPRECATED,
            },
            DecisionStatus.IMPLEMENTED: {
                DecisionStatus.DEPRECATED,
            },
        }

        return new_status in transitions.get(self, set())

