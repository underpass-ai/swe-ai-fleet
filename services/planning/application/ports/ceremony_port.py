"""Port (interface) for Ceremony management in Planning Service.

Following Hexagonal Architecture:
- Application layer defines the port (this interface)
- Infrastructure layer provides the adapter (gRPC client)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.statuses.backlog_review_role import (
    BacklogReviewRole,
)


@dataclass(frozen=True)
class AgentDeliberationRequest:
    """Request to add an agent deliberation to a ceremony.

    Attributes:
        ceremony_id: Ceremony identifier
        story_id: Story identifier
        role: Council role (BacklogReviewRole enum)
        agent_id: Specific agent identifier (e.g., "agent-architect-001")
        feedback: Council feedback/proposal text
        proposal: Full proposal/deliberation from agent (dict or str)
        reviewed_at: Timestamp when review was completed
    """

    ceremony_id: BacklogReviewCeremonyId
    story_id: StoryId
    role: BacklogReviewRole
    agent_id: str
    feedback: str
    proposal: dict | str
    reviewed_at: datetime


class CeremonyServiceError(Exception):
    """Raised when Ceremony Service communication fails."""

    pass


class CeremonyPort(ABC):
    """Port defining the interface for Ceremony management in Planning Service.

    This port abstracts Planning Service gRPC calls for ceremony management,
    allowing Task Extraction Service to update ceremonies without
    knowing Planning Service implementation details.

    Following Hexagonal Architecture:
    - Application layer defines the port (this interface)
    - Infrastructure layer provides the adapter (gRPC client)
    """

    @abstractmethod
    async def add_agent_deliberation(self, request: AgentDeliberationRequest) -> None:
        """Add an agent deliberation to a ceremony.

        This method:
        1. Updates the ceremony with the agent's deliberation
        2. Accumulates feedback from multiple roles
        3. Detects when all role deliberations are complete
        4. Publishes event when all deliberations complete

        Args:
            request: Agent deliberation request with all required fields

        Raises:
            CeremonyServiceError: If update fails
        """
        pass
