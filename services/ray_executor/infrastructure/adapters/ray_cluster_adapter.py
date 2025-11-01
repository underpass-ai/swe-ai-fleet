"""Ray cluster adapter implementation."""

import logging
import time
from typing import Any

import ray
from core.ray_jobs import RayAgentExecutor, RayAgentFactory

from services.ray_executor.domain.entities import DeliberationResult

logger = logging.getLogger(__name__)

# Create Ray remote actor from RayAgentExecutor
RayAgentJob = ray.remote(RayAgentExecutor)


class RayClusterAdapter:
    """Adapter for Ray cluster interaction.

    This adapter implements RayClusterPort using Ray client API.

    Following Hexagonal Architecture:
    - Implements port (interface) defined in domain
    - Translates domain entities to Ray-specific data structures
    - Handles Ray-specific errors and retries
    """

    def __init__(self, deliberations_registry: dict):
        """Initialize Ray cluster adapter.

        Args:
            deliberations_registry: Shared registry for tracking deliberations
        """
        self._deliberations = deliberations_registry

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
        """Submit deliberation to Ray cluster.

        Implements RayClusterPort.submit_deliberation()
        """
        # For now, we'll create one job per role (simplified)
        # TODO: Handle multiple agents properly
        agent_config = agents[0] if agents else None
        if not agent_config:
            raise ValueError("At least one agent required")

        # Use Factory to create executor with all dependencies injected
        executor = RayAgentFactory.create(
            agent_id=agent_config["agent_id"],
            role=agent_config["role"],
            vllm_url=vllm_url,
            model=vllm_model,
            nats_url=None,  # TODO: Get from config
            workspace_path=None,
            enable_tools=False,
        )

        # Create Ray remote actor from the configured executor
        agent_job = RayAgentJob.remote(
            config=executor.config,
            publisher=executor.publisher,
            vllm_client=executor.vllm_client,
            async_executor=executor.async_executor,
            vllm_agent=executor.vllm_agent,
        )

        # Submit to Ray
        future = agent_job.run.remote(
            task_id=task_id,
            task_description=task_description,
            constraints=constraints,
        )

        # Store deliberation info in registry
        self._deliberations[deliberation_id] = {
            'future': future,
            'task_id': task_id,
            'role': role,
            'status': 'running',
            'start_time': time.time(),
            'agents': [agent["agent_id"] for agent in agents],
        }

        return deliberation_id

    async def check_deliberation_status(
        self,
        deliberation_id: str,
    ) -> tuple[str, DeliberationResult | None, str | None]:
        """Check deliberation status on Ray cluster.

        Implements RayClusterPort.check_deliberation_status()

        Returns:
            Tuple of (status, result, error_message)
        """
        if deliberation_id not in self._deliberations:
            return ("not_found", None, f"Deliberation {deliberation_id} not found")

        deliberation = self._deliberations[deliberation_id]

        try:
            # Check if Ray job is ready
            if ray.wait([deliberation['future']], timeout=0.1)[0]:
                # Job completed
                result_data = ray.get(deliberation['future'])

                # Build DeliberationResult entity
                result = DeliberationResult(
                    agent_id=result_data.get('agent_id', 'unknown'),
                    proposal=result_data.get('proposal', ''),
                    reasoning=result_data.get('reasoning', ''),
                    score=result_data.get('score', 0.0),
                    metadata=result_data.get('metadata', {}),
                )

                return ("completed", result, None)

            else:
                # Job still running
                return ("running", None, None)

        except Exception as e:
            logger.error(f"❌ Error checking deliberation status: {e}")
            return ("failed", None, str(e))

    async def get_active_jobs(self) -> list[dict[str, Any]]:
        """Get list of active Ray jobs.

        Implements RayClusterPort.get_active_jobs()
        """
        # Return deliberations from registry
        # The use case will filter for running jobs
        return list(self._deliberations.items())

