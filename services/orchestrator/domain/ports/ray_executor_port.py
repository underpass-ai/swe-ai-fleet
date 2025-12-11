"""Port (interface) for Ray Executor communication."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from services.orchestrator.domain.entities import (
        DeliberationStatus,
        DeliberationSubmission,
    )


class RayExecutorPort(ABC):
    """Port defining the interface for Ray Executor communication.

    This port abstracts the communication with Ray Executor service,
    allowing the domain to remain independent of gRPC implementation details.

    Following Hexagonal Architecture:
    - Domain defines the port (this interface)
    - Infrastructure provides the adapter (gRPC implementation)
    """

    @abstractmethod
    async def execute_deliberation(
        self,
        task_id: str,
        task_description: str,
        role: str,
        agents: list[dict[str, Any]],
        constraints: dict[str, Any],
        vllm_url: str,
        vllm_model: str,
    ) -> DeliberationSubmission:
        """Execute deliberation on Ray cluster via Ray Executor (for task derivation - requires plan_id).

        Args:
            task_id: Unique task identifier
            task_description: Description of the task
            role: Role for the council (DEV, QA, etc.)
            agents: List of agent configurations
            constraints: Task constraints (must include plan_id)
            vllm_url: URL of vLLM server
            vllm_model: Model name to use

        Returns:
            DeliberationSubmission entity with submission result

        Raises:
            Exception: If submission fails
        """
        pass

    @abstractmethod
    async def get_deliberation_status(
        self,
        deliberation_id: str,
    ) -> DeliberationStatus:
        """Get status of a deliberation.

        Args:
            deliberation_id: Deliberation ID from execute_deliberation

        Returns:
            DeliberationStatus entity with current status

        Raises:
            Exception: If status check fails
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close connection to Ray Executor.

        Cleanup method to close gRPC channel and release resources.
        """
        pass

