"""Async deliberation use case using Ray jobs."""
from __future__ import annotations

import logging
import uuid
from typing import Any

import ray

from ..ray_jobs.vllm_agent_job import VLLMAgentJob

logger = logging.getLogger(__name__)


class DeliberateAsync:
    """
    Async use case for deliberation using Ray jobs.
    
    This use case:
    1. Receives a deliberation request
    2. Spawns N Ray jobs (one per agent)
    3. Returns immediately with task_id for tracking
    4. Agents publish results to NATS asynchronously
    
    Design decisions:
    - No blocking: returns immediately after submitting jobs
    - Agents communicate via NATS (fire-and-forget)
    - Result collection happens in NATS consumer
    - Ray handles job scheduling and failures
    """
    
    def __init__(
        self,
        ray_address: str | None = None,
        vllm_url: str = "http://vllm-server-service:8000",
        model: str = "Qwen/Qwen3-0.6B",
        nats_url: str = "nats://nats:4222",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: int = 60,
    ):
        """Initialize the async deliberation use case.
        
        Args:
            ray_address: Ray cluster address (e.g., "ray://ray-head:10001")
                        If None, will connect to existing Ray instance
            vllm_url: URL of the vLLM server
            model: Model name to use for agents
            nats_url: URL of the NATS server
            temperature: Default LLM temperature
            max_tokens: Default max tokens to generate
            timeout: Default timeout for LLM calls
        """
        self.ray_address = ray_address
        self.vllm_url = vllm_url
        self.model = model
        self.nats_url = nats_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        
        logger.info(
            f"DeliberateAsync initialized: "
            f"vllm={vllm_url}, model={model}, nats={nats_url}"
        )
    
    def connect_ray(self) -> None:
        """Connect to Ray cluster if not already connected."""
        if not ray.is_initialized():
            if self.ray_address:
                logger.info(f"Connecting to Ray cluster at {self.ray_address}")
                ray.init(address=self.ray_address, ignore_reinit_error=True)
            else:
                logger.info("Connecting to existing Ray instance")
                ray.init(ignore_reinit_error=True)
        else:
            logger.debug("Ray already initialized")
    
    def execute(
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
        Execute async deliberation by submitting Ray jobs.
        
        This method:
        1. Generates unique task_id if not provided
        2. Connects to Ray cluster
        3. Creates N agent jobs (with or without tools)
        4. Submits them to Ray (non-blocking)
        5. Returns immediately with tracking info
        
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
            - job_refs: List of Ray ObjectRefs for tracking
            - num_agents: Number of agents spawned
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
        
        # Connect to Ray
        self.connect_ray()
        
        logger.info(
            f"Starting async deliberation: task_id={task_id}, "
            f"role={role}, num_agents={num_agents}, rounds={rounds}, "
            f"enable_tools={enable_tools}"
        )
        
        # Validate rounds (only 1 round supported for now)
        if rounds != 1:
            logger.warning(
                f"Multiple rounds ({rounds}) requested but only 1 is supported. "
                f"Using rounds=1"
            )
            rounds = 1
        
        # Create and submit agent jobs
        job_refs = []
        agent_ids = []
        
        for i in range(num_agents):
            agent_id = f"agent-{role.lower()}-{i+1:03d}"
            agent_ids.append(agent_id)
            
            # Create Ray remote actor
            logger.debug(
                f"Creating Ray actor for {agent_id} "
                f"[tools={'enabled' if enable_tools else 'disabled'}]"
            )
            agent_actor = VLLMAgentJob.remote(
                agent_id=agent_id,
                role=role,
                vllm_url=self.vllm_url,
                model=self.model,
                nats_url=self.nats_url,
                workspace_path=workspace_path,  # NEW: Pass workspace
                enable_tools=enable_tools,       # NEW: Enable tool execution
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
            )
            
            # Submit job (non-blocking)
            # First agent: no diversity
            # Subsequent agents: with diversity for variety
            diversity = (i > 0)
            
            logger.debug(
                f"Submitting job for {agent_id} "
                f"(diversity={diversity})"
            )
            
            job_ref = agent_actor.run.remote(
                task_id=task_id,
                task_description=task_description,
                constraints=constraints,
                diversity=diversity,
            )
            
            job_refs.append(job_ref)
        
        logger.info(
            f"✅ Submitted {num_agents} agent jobs for task {task_id} "
            f"(agents: {', '.join(agent_ids)}, tools={'enabled' if enable_tools else 'disabled'})"
        )
        
        # Return tracking info (not waiting for results)
        return {
            "task_id": task_id,
            "job_refs": job_refs,  # Ray ObjectRefs for tracking
            "agent_ids": agent_ids,
            "num_agents": num_agents,
            "role": role,
            "rounds": rounds,
            "status": "submitted",
            "enable_tools": enable_tools,
            "workspace_path": workspace_path,
            "metadata": {
                "vllm_url": self.vllm_url,
                "model": self.model,
                "nats_url": self.nats_url,
                "diversity_enabled": num_agents > 1,
                "tools_enabled": enable_tools,
            }
        }
    
    def get_job_status(self, job_refs: list) -> dict[str, Any]:
        """
        Check status of Ray jobs (optional utility).
        
        Args:
            job_refs: List of Ray ObjectRefs from execute()
            
        Returns:
            Dictionary with job status summary
        """
        if not ray.is_initialized():
            return {
                "status": "error",
                "message": "Ray not initialized"
            }
        
        pending = 0
        completed = 0
        failed = 0
        
        for ref in job_refs:
            try:
                # Check if job is ready (non-blocking)
                ready, not_ready = ray.wait([ref], timeout=0)
                if ready:
                    # Job completed (success or failure)
                    try:
                        ray.get(ref, timeout=0)
                        completed += 1
                    except Exception:
                        failed += 1
                else:
                    pending += 1
            except Exception:
                failed += 1
        
        return {
            "total": len(job_refs),
            "pending": pending,
            "completed": completed,
            "failed": failed,
            "status": "in_progress" if pending > 0 else "done"
        }
    
    def shutdown(self) -> None:
        """Shutdown Ray connection (optional cleanup)."""
        if ray.is_initialized():
            logger.info("Shutting down Ray connection")
            ray.shutdown()

