"""AgentDeliberation value object."""

from dataclasses import dataclass
from datetime import datetime

from backlog_review_processor.domain.value_objects.statuses.backlog_review_role import (
    BacklogReviewRole,
)


@dataclass(frozen=True)
class AgentDeliberation:
    """
    Value Object: Individual agent's deliberation.

    Encapsulates a single agent's deliberation output from vLLM.

    Attributes:
        agent_id: Specific agent identifier (e.g., "agent-architect-001")
        role: Council role (BacklogReviewRole enum)
        proposal: Full proposal/deliberation from agent (dict or str)
        deliberated_at: Timestamp when deliberation was completed
    """

    agent_id: str
    role: BacklogReviewRole
    proposal: dict | str  # Full proposal from agent
    deliberated_at: datetime

    def __post_init__(self) -> None:
        """Validate value object (fail-fast).

        Raises:
            ValueError: If validation fails
        """
        if not self.agent_id or not self.agent_id.strip():
            raise ValueError("agent_id cannot be empty")

        if not isinstance(self.role, BacklogReviewRole):
            raise ValueError(
                f"role must be a BacklogReviewRole enum, got {type(self.role)}"
            )

    def get_feedback_text(self) -> str:
        """
        Extract feedback text from proposal.

        Returns:
            Feedback text (string representation of proposal)
        """
        if isinstance(self.proposal, dict):
            # Try to extract content from proposal dict
            return self.proposal.get("content", str(self.proposal))
        elif isinstance(self.proposal, str):
            return self.proposal
        else:
            return str(self.proposal)

    def __str__(self) -> str:
        """String representation for logging."""
        return (
            f"AgentDeliberation(agent_id={self.agent_id}, "
            f"role={self.role.value}, "
            f"deliberated_at={self.deliberated_at.isoformat()})"
        )
