"""
Ray job for executing vLLM agents asynchronously.

Integrates VLLMAgent for tool execution in addition to text generation.
Can operate in two modes:
1. With tools (enable_tools=True): Executes real operations (default)
2. Text-only (enable_tools=False): Generates proposals only (legacy deliberation)
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import aiohttp

try:
    import ray
    # Verify ray.remote is available (full Ray installation)
    if not hasattr(ray, 'remote'):
        raise ImportError("Ray installed but ray.remote not available")
    RAY_AVAILABLE = True
except (ImportError, AttributeError):
    RAY_AVAILABLE = False
    ray = None  # type: ignore

logger = logging.getLogger(__name__)


class VLLMAgentJobBase:
    """
    Ray remote actor that executes a vLLM agent with optional tool execution.
    
    This actor:
    1. Receives a task and constraints
    2. If tools enabled: Uses VLLMAgent to execute real operations (git, files, tests, etc)
    3. If tools disabled: Calls vLLM API to generate text proposal only
    4. Publishes the result to NATS (agent.response.completed)
    5. Handles failures gracefully
    
    Design decisions:
    - Each agent runs in its own Ray actor for isolation
    - Communication is async via NATS (fire-and-forget)
    - Failures are published to NATS for observability
    - Restarts are handled by Ray (max_restarts=2)
    - Tool execution is optional (enable_tools flag)
    
    Usage:
        # With tools (real execution)
        agent = VLLMAgentJob.remote(
            agent_id="agent-dev-001",
            role="DEV",
            vllm_url="http://vllm:8000",
            model="Qwen/Qwen3-0.6B",
            nats_url="nats://nats:4222",
            workspace_path="/workspace/project",
            enable_tools=True
        )
        
        # Text-only (legacy deliberation)
        agent = VLLMAgentJob.remote(
            agent_id="agent-dev-002",
            role="DEV",
            vllm_url="http://vllm:8000",
            model="Qwen/Qwen3-0.6B",
            nats_url="nats://nats:4222",
            enable_tools=False  # No workspace needed
        )
    """
    
    def __init__(
        self,
        agent_id: str,
        role: str,
        vllm_url: str,
        model: str,
        nats_url: str,
        workspace_path: str | Path | None = None,
        enable_tools: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: int = 60,
    ):
        """Initialize the vLLM agent job.
        
        Args:
            agent_id: Unique identifier for this agent (e.g., "agent-dev-001")
            role: Agent role (DEV, QA, ARCHITECT, DEVOPS, DATA)
            vllm_url: URL of the vLLM server (e.g., "http://vllm-server-service:8000")
            model: Model name to use (e.g., "Qwen/Qwen3-0.6B")
            nats_url: URL of the NATS server (e.g., "nats://nats:4222")
            workspace_path: Path to workspace (required if enable_tools=True)
            enable_tools: Whether to enable tool execution (default: False for backward compat)
            temperature: Sampling temperature for LLM
            max_tokens: Maximum tokens to generate
            timeout: Timeout in seconds for vLLM API calls
        """
        self.agent_id = agent_id
        self.role = role
        self.vllm_url = vllm_url
        self.model = model
        self.nats_url = nats_url
        self.workspace_path = Path(workspace_path) if workspace_path else None
        self.enable_tools = enable_tools
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        
        # Validate configuration
        if enable_tools and not workspace_path:
            raise ValueError("workspace_path required when enable_tools=True")
        
        # Initialize VLLMAgent (ALWAYS - for planning)
        # If enable_tools=False, agent can still plan but won't execute
        self.vllm_agent = None
        if workspace_path:  # Need workspace to initialize agent
            from swe_ai_fleet.agents import VLLMAgent
            self.vllm_agent = VLLMAgent(
                agent_id=agent_id,
                role=role,
                workspace_path=self.workspace_path,
                vllm_url=vllm_url,
                enable_tools=enable_tools,  # Agent respects this flag
            )
        
        logger.info(
            f"VLLMAgentJob initialized: {agent_id} ({role}) "
            f"using model {model} at {vllm_url} "
            f"[tools={'enabled' if enable_tools else 'disabled'}]"
        )
    
    def run(
        self,
        task_id: str,
        task_description: str,
        constraints: dict[str, Any],
        diversity: bool = False,
    ) -> dict[str, Any]:
        """
        Execute the agent job synchronously (Ray will handle async execution).
        
        This is a sync wrapper around the async implementation for Ray compatibility.
        
        Args:
            task_id: Unique task identifier
            task_description: Description of the task to solve
            constraints: Task constraints (rubric, requirements, etc.)
            diversity: Whether to increase diversity in the response
            
        Returns:
            Result dictionary with proposal and metadata
        """
        return asyncio.run(self._run_async(task_id, task_description, constraints, diversity))
    
    async def _run_async(
        self,
        task_id: str,
        task_description: str,
        constraints: dict[str, Any],
        diversity: bool = False,
    ) -> dict[str, Any]:
        """
        Async implementation of agent job execution.
        
        Flow (with tools):
        1. Connect to NATS
        2. Execute task using VLLMAgent (with real tool execution)
        3. Publish result with operations + artifacts to NATS
        4. Handle errors and publish failures
        
        Flow (text-only):
        1. Connect to NATS
        2. Generate proposal using vLLM API
        3. Publish text result to NATS
        4. Handle errors
        """
        nats_client = None
        start_time = time.time()
        
        try:
            # Import NATS here to avoid dependency issues
            import nats
            from nats.js import JetStreamContext
            
            # 1. Connect to NATS
            logger.debug(f"[{self.agent_id}] Connecting to NATS at {self.nats_url}")
            nats_client = await nats.connect(self.nats_url)
            js: JetStreamContext = nats_client.jetstream()
            
            # 2. Execute task using VLLMAgent (with or without tool execution)
            if self.vllm_agent:
                # Use VLLMAgent (can plan and optionally execute tools)
                mode = "with tools" if self.enable_tools else "planning only"
                logger.info(
                    f"[{self.agent_id}] Executing task {task_id} {mode} "
                    f"(workspace={self.workspace_path})"
                )
                
                # Get context from constraints
                context = constraints.get("context", "")
                
                # Execute task using VLLMAgent
                # If enable_tools=False, agent will generate plan but not execute
                agent_result = await self.vllm_agent.execute_task(
                    task=task_description,
                    context=context,
                    constraints=constraints,
                )
                
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Prepare result with operations (may be empty if enable_tools=False)
                result = {
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                    "role": self.role,
                    "status": "completed" if agent_result.success else "failed",
                    "success": agent_result.success,
                    "operations": agent_result.operations,  # May be empty list
                    "artifacts": agent_result.artifacts,    # May be empty dict
                    "audit_trail": agent_result.audit_trail,
                    "error": agent_result.error,
                    "duration_ms": duration_ms,
                    "timestamp": datetime.utcnow().isoformat(),
                    "model": self.model,
                    "enable_tools": self.enable_tools,
                }
            else:
                # FALLBACK: Legacy vLLM API call (only if no workspace provided)
                # This is for backward compatibility with old code
                logger.info(
                    f"[{self.agent_id}] Generating text proposal for task {task_id} "
                    f"(legacy mode - no VLLMAgent, diversity={diversity})"
                )
                proposal = await self._generate_proposal(
                    task_description, constraints, diversity
                )
                
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Prepare result (legacy format)
                result = {
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                    "role": self.role,
                    "proposal": proposal,
                    "status": "completed",
                    "duration_ms": duration_ms,
                    "timestamp": datetime.utcnow().isoformat(),
                    "model": self.model,
                    "diversity": diversity,
                    "enable_tools": False,
                }
            
            # 3. Publish to NATS
            logger.info(
                f"[{self.agent_id}] Publishing result to NATS "
                f"(duration={duration_ms}ms)"
            )
            await js.publish(
                subject="agent.response.completed",
                payload=json.dumps(result).encode(),
            )
            
            logger.info(f"[{self.agent_id}] ✅ Job completed successfully")
            return result
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[{self.agent_id}] ❌ Job failed: {e}", exc_info=True)
            
            # Publish error to NATS
            error_result = {
                "task_id": task_id,
                "agent_id": self.agent_id,
                "role": self.role,
                "status": "failed",
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_ms": duration_ms,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            if nats_client:
                try:
                    js = nats_client.jetstream()
                    await js.publish(
                        subject="agent.response.failed",
                        payload=json.dumps(error_result).encode(),
                    )
                except Exception as publish_error:
                    logger.error(
                        f"[{self.agent_id}] Failed to publish error to NATS: "
                        f"{publish_error}"
                    )
            
            raise
        
        finally:
            # Close NATS connection
            if nats_client:
                await nats_client.close()
    
    async def _generate_proposal(
        self, task: str, constraints: dict, diversity: bool
    ) -> dict[str, Any]:
        """
        Generate a proposal using vLLM API.
        
        Args:
            task: Task description
            constraints: Task constraints
            diversity: Whether to increase diversity
            
        Returns:
            Proposal dictionary with content and metadata
        """
        # Build prompts
        system_prompt = self._build_system_prompt(constraints, diversity)
        user_prompt = self._build_task_prompt(task, constraints)
        
        # Adjust temperature for diversity
        temperature = self.temperature * 1.3 if diversity else self.temperature
        
        # Prepare vLLM API request
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": self.max_tokens,
        }
        
        # Call vLLM API
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.vllm_url}/v1/chat/completions",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    # Extract content from response
                    content = data["choices"][0]["message"]["content"]
                    
                    return {
                        "content": content.strip(),
                        "author_id": self.agent_id,
                        "author_role": self.role,
                        "model": self.model,
                        "temperature": temperature,
                        "tokens": data.get("usage", {}).get("total_tokens", 0),
                    }
                    
            except aiohttp.ClientError as e:
                logger.error(
                    f"[{self.agent_id}] vLLM API error: {e}",
                    exc_info=True
                )
                raise RuntimeError(f"Failed to call vLLM API: {e}") from e
            except KeyError as e:
                logger.error(
                    f"[{self.agent_id}] Invalid vLLM response format: {e}",
                    exc_info=True
                )
                raise RuntimeError(f"Invalid vLLM response: {e}") from e
    
    def _build_system_prompt(self, constraints: dict, diversity: bool) -> str:
        """
        Build system prompt based on role and constraints.
        
        Args:
            constraints: Task constraints
            diversity: Whether to increase diversity
            
        Returns:
            System prompt string
        """
        role_context = {
            "DEV": "You are an expert software developer. Focus on writing clean, "
                   "maintainable, well-tested code following best practices.",
            "QA": "You are an expert quality assurance engineer. Focus on testing "
                  "strategies, edge cases, and potential bugs.",
            "ARCHITECT": "You are a senior software architect. Focus on system design, "
                        "scalability, and architectural patterns.",
            "DEVOPS": "You are a DevOps engineer. Focus on deployment, CI/CD, "
                     "infrastructure, and reliability.",
            "DATA": "You are a data engineer. Focus on data pipelines, ETL, "
                   "databases, and data quality.",
        }
        
        base_prompt = role_context.get(
            self.role,
            f"You are an expert {self.role} engineer."
        )
        
        # Add rubric if present
        rubric = constraints.get("rubric", "")
        if rubric:
            base_prompt += f"\n\nEvaluation rubric:\n{rubric}"
        
        # Add requirements if present
        requirements = constraints.get("requirements", [])
        if requirements:
            req_text = "\n".join(f"- {req}" for req in requirements)
            base_prompt += f"\n\nRequirements:\n{req_text}"
        
        # Add diversity instruction
        if diversity:
            base_prompt += (
                "\n\nIMPORTANT: Provide a creative and diverse approach. "
                "Think outside the box and offer alternative perspectives."
            )
        
        return base_prompt
    
    def _build_task_prompt(self, task: str, constraints: dict) -> str:
        """
        Build user prompt for the task.
        
        Args:
            task: Task description
            constraints: Task constraints
            
        Returns:
            User prompt string
        """
        prompt = f"Task: {task}\n\n"
        prompt += "Please provide a detailed proposal for implementing this task.\n\n"
        prompt += "Your response should include:\n"
        prompt += "1. Analysis of the requirements\n"
        prompt += "2. Proposed solution approach\n"
        prompt += "3. Implementation details\n"
        prompt += "4. Potential challenges and how to address them\n"
        
        # Add metadata constraints if present
        metadata = constraints.get("metadata", {})
        if metadata:
            prompt += "\n\nAdditional context:\n"
            for key, value in metadata.items():
                prompt += f"- {key}: {value}\n"
        
        return prompt
    
    def get_info(self) -> dict[str, Any]:
        """Get information about this agent job.
        
        Returns:
            Dictionary with agent information
        """
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "model": self.model,
            "vllm_url": self.vllm_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }


# Ray remote actor wrapper
if RAY_AVAILABLE:
    @ray.remote(num_cpus=1, max_restarts=2)
    class VLLMAgentJob(VLLMAgentJobBase):
        """Ray remote actor version of VLLMAgentJobBase.
        
        This is the actual class that should be used in Ray clusters.
        For testing, use VLLMAgentJobBase directly.
        """
        pass
else:
    # Fallback for environments without Ray (tests, CI)
    class VLLMAgentJob(VLLMAgentJobBase):  # type: ignore
        """Fallback version without Ray decorator for testing environments."""
        pass

