"""Port (interface) for Ray Executor communication.

Following Hexagonal Architecture:
- Application layer defines the port (this interface)
- Infrastructure layer provides the adapter (gRPC client)
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from backlog_review_processor.domain.value_objects.identifiers.deliberation_id import DeliberationId
from backlog_review_processor.domain.value_objects.identifiers.story_id import StoryId
from backlog_review_processor.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)


class RayExecutorError(Exception):
    """Raised when Ray Executor communication fails."""

    pass


class RayExecutorPort(ABC):
    """Port defining the interface for Ray Executor communication.

    This port abstracts Ray Executor gRPC calls,
    allowing Task Extraction Service to submit LLM jobs without
    knowing Ray Executor implementation details.

    Following Hexagonal Architecture:
    - Application layer defines the port (this interface)
    - Infrastructure layer provides the adapter (gRPC client)

    Design: Event-Driven (Fire-and-Forget)
    - submit_task_extraction() returns immediately with DeliberationId
    - Actual execution happens asynchronously in Ray cluster
    - Result published to NATS by Ray Worker (agent.response.completed)
    - Consumer handles result processing
    """

    @abstractmethod
    async def submit_task_extraction(
        self,
        task_id: str,
        task_description: str,
        story_id: StoryId,
        ceremony_id: BacklogReviewCeremonyId,
    ) -> DeliberationId:
        """Submit task extraction job to Ray Executor.

        Fire-and-forget pattern:
        1. Submits job to Ray Executor (gRPC ExecuteDeliberation)
        2. Returns DeliberationId immediately
        3. Ray executes asynchronously with vLLM agent
        4. Result published to NATS (agent.response.completed with task extraction results)

        Args:
            task_id: Task identifier (format: "ceremony-{id}:story-{id}:task-extraction")
            task_description: Prompt with all agent deliberations for task extraction
            story_id: Story identifier
            ceremony_id: Ceremony identifier

        Returns:
            DeliberationId for tracking the async job

        Raises:
            RayExecutorError: If submission fails
        """
        pass

