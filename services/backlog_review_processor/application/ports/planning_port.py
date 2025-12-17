"""Port (interface) for Planning Service communication.

Following Hexagonal Architecture:
- Application layer defines the port (this interface)
- Infrastructure layer provides the adapter (gRPC client)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from backlog_review_processor.domain.value_objects.identifiers.story_id import StoryId
from backlog_review_processor.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)


@dataclass(frozen=True)
class TaskCreationRequest:
    """Request to create a task in Planning Service.

    Attributes:
        story_id: Story identifier
        title: Task title
        description: Task description
        estimated_hours: Estimated hours for the task
        deliberation_indices: List of indices into ceremony's agent_deliberations
        ceremony_id: Ceremony identifier (for storing deliberation relationship)
    """

    story_id: StoryId
    title: str
    description: str
    estimated_hours: int
    deliberation_indices: list[int]
    ceremony_id: BacklogReviewCeremonyId


class PlanningServiceError(Exception):
    """Raised when Planning Service communication fails."""

    pass


class PlanningPort(ABC):
    """Port defining the interface for Planning Service communication.

    This port abstracts Planning Service gRPC calls,
    allowing Task Extraction Service to create tasks without
    knowing Planning Service implementation details.

    Following Hexagonal Architecture:
    - Application layer defines the port (this interface)
    - Infrastructure layer provides the adapter (gRPC client)
    """

    @abstractmethod
    async def create_task(self, request: TaskCreationRequest) -> str:
        """Create a task in Planning Service.

        Args:
            request: Task creation request with all required fields

        Returns:
            Task ID of the created task

        Raises:
            PlanningServiceError: If creation fails
        """
        pass

