"""Port for Ray cluster interaction."""

from typing import Any, Protocol

from services.ray_executor.domain.entities import (
    DeliberationResult,
    MultiAgentDeliberationResult,
)


class RayClusterPort(Protocol):
    """Port defining the interface for Ray cluster operations.

    This port abstracts the Ray cluster communication, allowing the domain
    to remain independent of Ray implementation details.

    Following Hexagonal Architecture (Dependency Inversion Principle):
    - Domain defines the port (this interface)
    - Infrastructure provides the adapter (Ray client implementation)
    """

    async def submit_deliberation(
        self,
        deliberation_id: str,
        task_id: str,
        task_description: str,
        role: str,
        agents: list[dict[str, Any]],
        constraints: dict[str, Any],
        vllm_url: str,
        vllm_model: str,
    ) -> str:
        """Submit a deliberation task to the Ray cluster.

        Args:
            deliberation_id: Unique identifier for this deliberation
            task_id: Task identifier
            task_description: What needs to be done
            role: Agent role (DEV, QA, etc.)
            agents: List of agent configurations
            constraints: Task constraints (timeouts, retries, etc.)
            vllm_url: URL of vLLM inference server
            vllm_model: Model name to use

        Returns:
            Ray job submission ID

        Raises:
            Exception: If submission fails
        """
        ...

    async def check_deliberation_status(
        self,
        deliberation_id: str,
    ) -> tuple[str, DeliberationResult | MultiAgentDeliberationResult | None, str | None]:
        """Check the status of a running deliberation.

        Args:
            deliberation_id: Unique identifier for the deliberation

        Returns:
            Tuple of (status, result, error_message)
            - status: "running", "completed", "failed", or "not_found"
            - result: DeliberationResult (single agent) or MultiAgentDeliberationResult (multiple agents) if completed, None otherwise
            - error_message: Error message if failed, None otherwise
        """
        ...

    async def get_active_jobs(self) -> list[dict[str, Any]]:
        """Get list of active Ray jobs.

        Returns:
            List of job information dictionaries
        """
        ...

