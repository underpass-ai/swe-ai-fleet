"""BacklogReviewContextRequest domain entity.

Represents a request for context retrieval during backlog review ceremonies.
Encapsulates all parameters needed to fetch role-specific context for a story.
"""

from dataclasses import dataclass

from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.statuses.backlog_review_phase import (
    BacklogReviewPhase,
)
from planning.domain.value_objects.statuses.backlog_review_role import (
    BacklogReviewRole,
)
from planning.domain.value_objects.statuses.token_budget import TokenBudget


@dataclass(frozen=True)
class BacklogReviewContextRequest:
    """
    Request for context retrieval during backlog review.

    This entity encapsulates the parameters needed to fetch context
    from Context Service for a specific story, role, and phase during
    backlog review ceremonies.

    Domain Invariants:
    - story_id must be valid (non-empty StoryId)
    - role must be one of the valid review roles (ARCHITECT, QA, DEVOPS)
    - phase must be a valid BacklogReviewPhase
    - token_budget must be positive (> 0)

    Immutability: frozen=True ensures no mutation after creation.
    """

    story_id: StoryId
    role: BacklogReviewRole
    phase: BacklogReviewPhase
    token_budget: TokenBudget = TokenBudget.STANDARD

    def __post_init__(self) -> None:
        """Validate request parameters (fail-fast).

        Raises:
            ValueError: If any parameter is invalid
        """
        # StoryId validation already ensures non-empty, but double-check
        if not self.story_id:
            raise ValueError("story_id cannot be None")

        if not isinstance(self.role, BacklogReviewRole):
            raise ValueError(
                f"role must be a BacklogReviewRole enum, got {type(self.role)}"
            )

        if not isinstance(self.phase, BacklogReviewPhase):
            raise ValueError(
                f"phase must be a BacklogReviewPhase enum, got {type(self.phase)}"
            )

        if not isinstance(self.token_budget, TokenBudget):
            raise ValueError(
                f"token_budget must be a TokenBudget enum, got {type(self.token_budget)}"
            )

    @classmethod
    def build_for_design_phase(
        cls,
        story_id: StoryId,
        role: BacklogReviewRole,
        token_budget: TokenBudget = TokenBudget.STANDARD,
    ) -> "BacklogReviewContextRequest":
        """
        Build context request for DESIGN phase (builder method).

        Creates a context request with DESIGN phase, which is the standard
        phase for backlog review ceremonies (planning/design phase).

        Args:
            story_id: Story identifier
            role: Review role (BacklogReviewRole enum)
            token_budget: Token budget (default: TokenBudget.STANDARD = 2000)

        Returns:
            BacklogReviewContextRequest with DESIGN phase

        Raises:
            ValueError: If any parameter is invalid
        """
        return cls(
            story_id=story_id,
            role=role,
            phase=BacklogReviewPhase.DESIGN,
            token_budget=token_budget,
        )

    def to_context_port_params(self) -> dict[str, str | int]:
        """Convert to parameters for ContextPort.get_context().

        Returns:
            Dictionary with parameters for ContextPort interface
        """
        return {
            "story_id": self.story_id.value,
            "role": self.role.value,  # Convert enum to string for port
            "phase": self.phase.value,
            "token_budget": self.token_budget.value,  # Convert enum to int for port
        }
