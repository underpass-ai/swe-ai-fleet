"""AgentDeliberation - Value Object for individual agent deliberation.

Value Object (Domain Layer):
- Immutable record of a single agent's deliberation
- Contains agent_id, role, proposal content, and timestamp
- Used to track all agent deliberations for a story

Following DDD:
- Immutable (@dataclass(frozen=True))
- Fail-fast validation
- Rich domain model with deliberation semantics
"""

from dataclasses import dataclass
from datetime import datetime

from planning.domain.value_objects.statuses.backlog_review_role import (
    BacklogReviewRole,
)


@dataclass(frozen=True)
class AgentDeliberation:
    """
    Value Object: Individual agent deliberation for a story.

    Represents a single agent's deliberation output during backlog review.
    Each agent produces a deliberation (proposal/feedback) that contributes
    to the overall story review.

    Domain Invariants:
    - agent_id cannot be empty
    - role must be valid BacklogReviewRole
    - proposal cannot be empty (dict or str)
    - deliberated_at must be valid datetime

    Usage:
        deliberation = AgentDeliberation(
            agent_id="agent-architect-001",
            role=BacklogReviewRole.ARCHITECT,
            proposal={"content": "Analysis: ...", "tasks": [...]},
            deliberated_at=datetime.now(UTC),
        )
    """

    agent_id: str  # e.g., "agent-architect-001"
    role: BacklogReviewRole  # ARCHITECT, QA, or DEVOPS
    proposal: dict | str  # Full proposal/deliberation from agent
    deliberated_at: datetime  # When deliberation was completed

    def __post_init__(self) -> None:
        """
        Validate AgentDeliberation (fail-fast).

        Raises:
            ValueError: If validation fails
        """
        if not self.agent_id or not self.agent_id.strip():
            raise ValueError("agent_id cannot be empty")

        if not isinstance(self.role, BacklogReviewRole):
            raise ValueError(
                f"role must be a BacklogReviewRole enum, got {type(self.role)}"
            )

        if not self.proposal:
            raise ValueError("proposal cannot be empty")

        if isinstance(self.proposal, str) and not self.proposal.strip():
            raise ValueError("proposal string cannot be empty")

    def get_feedback_text(self) -> str:
        """
        Extract feedback text from proposal.

        Handles both dict and str proposals.

        Returns:
            Feedback text as string
        """
        if isinstance(self.proposal, dict):
            return self.proposal.get("content", str(self.proposal))
        return str(self.proposal)

