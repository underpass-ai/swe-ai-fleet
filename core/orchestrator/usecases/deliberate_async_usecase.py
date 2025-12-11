"""Async deliberation use case using Ray Executor gRPC service."""
from __future__ import annotations

import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)


class DeliberateAsync:
    """
    Async use case for deliberation using Ray Executor gRPC service.

    This use case:
    1. Receives a deliberation request
    2. Calls Ray Executor via gRPC to submit jobs
    3. Returns immediately with deliberation_id for tracking
    4. Ray Executor handles Ray cluster communication
    5. Agents publish results to NATS asynchronously

    Design decisions:
    - No blocking: returns immediately after gRPC call
    - Ray Executor handles Python version compatibility
    - Agents communicate via NATS (fire-and-forget)
    - Result collection happens in NATS consumer
    """

    def __init__(
        self,
        ray_executor_stub,
        vllm_url: str = "http://vllm-server-service:8000",
        model: str = "Qwen/Qwen3-0.6B",
        nats_url: str = "nats://nats:4222",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: int = 60,
    ):
        """Initialize the async deliberation use case.

        Args:
            ray_executor_stub: gRPC stub for Ray Executor service
            vllm_url: URL of the vLLM server
            model: Model name to use for agents
            nats_url: URL of the NATS server
            temperature: Default LLM temperature
            max_tokens: Default max tokens to generate
            timeout: Default timeout for LLM calls
        """
        self.ray_executor = ray_executor_stub
        self.vllm_url = vllm_url
        self.model = model
        self.nats_url = nats_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

        logger.info(
            f"DeliberateAsync initialized with Ray Executor gRPC: "
            f"vllm={vllm_url}, model={model}, nats={nats_url}"
        )

    # NOTE: connect_ray() removed - Ray Executor handles Ray connection

    async def execute(
        self,
        task_id: str | None,
        task_description: str,
        role: str,
        num_agents: int = 3,
        constraints: dict[str, Any] | None = None,
        rounds: int = 1,
        workspace_path: str | None = None,
        enable_tools: bool = False,
    ) -> dict[str, Any]:
        """
        Execute async deliberation by calling Ray Executor service.

        This method:
        1. Generates unique task_id if not provided
        2. Calls Ray Executor via gRPC to submit jobs
        3. Ray Executor handles Ray cluster communication
        4. Returns immediately with tracking info

        Args:
            task_id: Unique task identifier (generated if None)
            task_description: Description of the task
            role: Role for the council (DEV, QA, ARCHITECT, etc.)
            num_agents: Number of agents to spawn
            constraints: Task constraints (rubric, requirements, etc.)
            rounds: Number of deliberation rounds (currently only 1 supported)
            workspace_path: Path to workspace (required if enable_tools=True)
            enable_tools: Whether to enable tool execution (default: False)

        Returns:
            Dictionary with:
            - task_id: Unique task identifier
            - deliberation_id: ID from Ray Executor
            - num_agents: Number of agents requested
            - status: "submitted"
            - metadata: Additional tracking info

        Raises:
            ValueError: If enable_tools=True but workspace_path not provided
        """
        # Generate task_id if not provided
        if task_id is None:
            task_id = f"task-{uuid.uuid4()}"

        # Ensure constraints is a dict
        if constraints is None:
            constraints = {}

        # Validate tool configuration
        if enable_tools and not workspace_path:
            raise ValueError("workspace_path required when enable_tools=True")

        logger.info(
            f"Starting async deliberation via Ray Executor: task_id={task_id}, "
            f"role={role}, num_agents={num_agents}, enable_tools={enable_tools}"
        )

        # Validate rounds (only 1 round supported for now)
        if rounds != 1:
            logger.warning(
                f"Multiple rounds ({rounds}) requested but only 1 is supported. "
                f"Using rounds=1"
            )
            rounds = 1

        # Build agents list as dicts (for RayExecutorPort interface)
        agents = []
        for i in range(num_agents):
            agent_id = f"agent-{role.lower()}-{i+1:03d}"
            agents.append({
                "id": agent_id,
                "role": role,
                "model": self.model,
                "prompt_template": ""  # Will be set by Ray Executor
            })

        # Call Ray Executor via port interface
        # Use backlog review endpoint if no plan_id (backlog review ceremony)
        # Use regular endpoint if plan_id is present (task derivation ceremony)
        has_plan_id = constraints.get("plan_id") and constraints.get("plan_id").strip()

        try:
            if has_plan_id:
                # Task derivation ceremony - use regular endpoint (requires plan_id)
                submission = await self.ray_executor.execute_deliberation(
                    task_id=task_id,
                    task_description=task_description,
                    role=role,
                    agents=agents,
                    constraints=constraints,
                    vllm_url=self.vllm_url,
                    vllm_model=self.model,
                )
            else:
                # Backlog review ceremony - use backlog review endpoint (no plan_id)
                submission = await self.ray_executor.execute_backlog_review_deliberation(
                    task_id=task_id,
                    task_description=task_description,
                    role=role,
                    agents=agents,
                    constraints=constraints,
                    vllm_url=self.vllm_url,
                    vllm_model=self.model,
                )

            logger.info(
                f"✅ Ray Executor accepted deliberation: {submission.deliberation_id} "
                f"(status: {submission.status})"
            )

            # Return tracking info (not waiting for results)
            return {
                "task_id": task_id,
                "deliberation_id": submission.deliberation_id,
                "num_agents": num_agents,
                "role": role,
                "status": submission.status,
                "message": submission.message,
                "enable_tools": enable_tools,
                "metadata": {
                    "vllm_url": self.vllm_url,
                    "model": self.model,
                    "nats_url": self.nats_url,
                    "diversity_enabled": num_agents > 1,
                    "tools_enabled": enable_tools,
                }
            }

        except Exception as e:
            logger.error(f"❌ Failed to submit deliberation to Ray Executor: {e}")
            raise

    async def get_deliberation_status(self, deliberation_id: str) -> dict[str, Any]:
        """
        Check status of deliberation via Ray Executor.

        Args:
            deliberation_id: Deliberation ID from execute()

        Returns:
            Dictionary with deliberation status
        """
        from gen import ray_executor_pb2

        request = ray_executor_pb2.GetDeliberationStatusRequest(
            deliberation_id=deliberation_id
        )

        try:
            response = await self.ray_executor.GetDeliberationStatus(request)

            return {
                "deliberation_id": deliberation_id,
                "status": response.status,
                "result": response.result if response.HasField("result") else None,
                "error_message": response.error_message if response.error_message else None
            }
        except Exception as e:
            logger.error(f"Failed to get deliberation status: {e}")
            return {
                "deliberation_id": deliberation_id,
                "status": "error",
                "error_message": str(e)
            }

    # DEPRECATED: No longer needed - Ray Executor handles this
    def get_job_status(self) -> dict[str, Any]:
        """
        DEPRECATED: Use get_deliberation_status() instead.
        This method is kept for backwards compatibility but does nothing.
        """
        logger.warning("get_job_status() is deprecated. Use get_deliberation_status() instead.")
        return {
            "status": "deprecated",
            "message": "Use get_deliberation_status() instead"
        }

    # DEPRECATED methods removed - Ray Executor handles Ray connection and job tracking

