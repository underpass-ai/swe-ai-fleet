"""Execute deliberation use case."""

import logging
import time
from dataclasses import dataclass

from services.ray_executor.domain.entities import DeliberationRequest
from services.ray_executor.domain.ports import NATSPublisherPort, RayClusterPort

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExecuteDeliberationResult:
    """Result of execute deliberation use case.

    Attributes:
        deliberation_id: Unique identifier for the deliberation
        status: Submission status ("submitted" or "failed")
        message: Human-readable status message
    """

    deliberation_id: str
    status: str
    message: str


class ExecuteDeliberationUseCase:
    """Use case for executing a deliberation on the Ray cluster.

    This use case orchestrates the submission of a deliberation task to Ray
    and publishes streaming events via NATS.

    Responsibilities:
    - Generate unique deliberation ID
    - Submit task to Ray cluster via RayClusterPort
    - Publish stream start event via NATSPublisherPort
    - Track statistics
    - Return submission result

    Following Hexagonal Architecture:
    - Depends only on ports (interfaces), not concrete implementations
    - All dependencies injected via constructor
    """

    def __init__(
        self,
        ray_cluster: RayClusterPort,
        nats_publisher: NATSPublisherPort | None,
        stats_tracker: dict,
    ):
        """Initialize use case with dependencies.

        Args:
            ray_cluster: Port for Ray cluster interaction
            nats_publisher: Port for NATS publishing (optional)
            stats_tracker: Shared statistics dictionary
        """
        self._ray_cluster = ray_cluster
        self._nats_publisher = nats_publisher
        self._stats = stats_tracker

    async def execute(
        self,
        request: DeliberationRequest,
    ) -> ExecuteDeliberationResult:
        """Execute the deliberation submission use case.

        Args:
            request: Deliberation request entity

        Returns:
            ExecuteDeliberationResult with submission status
        """
        # Generate unique deliberation ID
        deliberation_id = f"deliberation-{request.task_id}-{int(time.time())}"

        logger.info(f"🚀 Executing deliberation: {deliberation_id}")
        logger.info(f"   Task ID: {request.task_id}")
        logger.info(f"   Role: {request.role}")
        logger.info(f"   Agents: {len(request.agents)}")
        logger.info(f"   Task Description (full):\n{'='*80}\n{request.task_description}\n{'='*80}")
        # constraints is always present (required field in DeliberationRequest)
        constraints_dict = {
            "story_id": request.constraints.story_id,
            "plan_id": request.constraints.plan_id,
            "timeout_seconds": request.constraints.timeout_seconds,
            "max_retries": request.constraints.max_retries,
            "metadata": request.constraints.metadata,
        }
        logger.info(f"   Constraints: {constraints_dict}")

        try:
            # Convert domain entities to dicts for Ray submission
            agents_data = [
                {
                    "agent_id": agent.agent_id,
                    "role": agent.role,
                    "model": agent.model,
                    "prompt_template": agent.prompt_template,
                }
                for agent in request.agents
            ]

            # Build constraints dict, preserving metadata (including original task_id from planning)
            constraints_data = {
                "story_id": request.constraints.story_id,
                "plan_id": request.constraints.plan_id,
                "timeout": request.constraints.timeout_seconds,
                "max_retries": request.constraints.max_retries,
            }

            # Preserve metadata if it exists (contains original task_id from planning)
            if request.constraints.metadata:
                constraints_data["metadata"] = request.constraints.metadata

            # Submit to Ray cluster
            logger.info("📤 Submitting to Ray cluster...")
            await self._ray_cluster.submit_deliberation(
                deliberation_id=deliberation_id,
                task_id=request.task_id,
                task_description=request.task_description,
                role=request.role,
                agents=agents_data,
                constraints=constraints_data,
                vllm_url=request.vllm_url,
                vllm_model=request.vllm_model,
            )

            # Update statistics
            self._stats['total_deliberations'] += 1
            self._stats['active_deliberations'] += 1

            # Publish stream start event if NATS available
            if self._nats_publisher:
                await self._nats_publisher.publish_stream_event(
                    event_type="vllm_stream_start",
                    agent_id=deliberation_id,
                    data={
                        "task_description": request.task_description,
                        "role": request.role,
                        "status": "streaming",
                        "model": request.vllm_model,
                        "deliberation_id": deliberation_id,
                    },
                )

            logger.info(f"✅ Deliberation submitted to Ray: {deliberation_id}")

            return ExecuteDeliberationResult(
                deliberation_id=deliberation_id,
                status="submitted",
                message="Deliberation submitted to Ray cluster",
            )

        except Exception as e:
            logger.error(f"❌ Failed to execute deliberation: {e}")
            self._stats['failed_deliberations'] += 1

            return ExecuteDeliberationResult(
                deliberation_id=deliberation_id,
                status="failed",
                message=f"Failed to execute deliberation: {str(e)}",
            )

