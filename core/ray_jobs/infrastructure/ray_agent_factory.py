"""Factory para crear RayAgentExecutor con todas sus dependencias."""

import logging
from pathlib import Path
from typing import Any

from ..domain import AgentConfig
from .adapters import (
    RayAgentExecutor,
    NATSResultPublisher,
    VLLMHTTPClient,
    AsyncioExecutor,
)

logger = logging.getLogger(__name__)

# VLLMAgent and AgentInitializationConfig will be imported lazily when needed


class RayAgentFactory:
    """
    Factory para crear RayAgentExecutor con dependencias inyectadas.

    Responsabilidad: Composition root (dependency injection).

    Crea y conecta:
    - AgentConfig (domain)
    - NATSResultPublisher (infrastructure)
    - VLLMHTTPClient (infrastructure)
    - AsyncioExecutor (infrastructure)
    - VLLMAgent (external component, optional)
    - RayAgentExecutor (infrastructure)
    """

    @staticmethod
    def create(
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
    ) -> RayAgentExecutor:
        """
        Crear RayAgentExecutor con todas las dependencias inyectadas.

        Args:
            agent_id: Unique identifier for this agent (e.g., "agent-dev-001")
            role: Agent role (DEV, QA, ARCHITECT, DEVOPS, DATA)
            vllm_url: URL of the vLLM server (e.g., "http://vllm-server-service:8000")
            model: Model name to use (e.g., "Qwen/Qwen3-0.6B")
            nats_url: URL of the NATS server (e.g., "nats://nats:4222")
            workspace_path: Path to workspace (required if enable_tools=True)
            enable_tools: Whether to enable tool execution (default: False)
            temperature: Sampling temperature for LLM
            max_tokens: Maximum tokens to generate
            timeout: Timeout in seconds for vLLM API calls

        Returns:
            RayAgentExecutor with all dependencies injected

        Raises:
            ValueError: If enable_tools=True but workspace_path is None
            ValueError: If enable_tools=True but VLLMAgent is not available
        """
        # 1. Create and validate configuration (domain model)
        config = AgentConfig.create(
            agent_id=agent_id,
            role=role,
            model=model,
            vllm_url=vllm_url,
            nats_url=nats_url,
            workspace_path=workspace_path,
            enable_tools=enable_tools,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )

        # 2. Create infrastructure adapters
        publisher = NATSResultPublisher(nats_url)

        vllm_client = VLLMHTTPClient(
            vllm_url=vllm_url,
            agent_id=agent_id,
            role=role,
            model=model,
            timeout=timeout,
        )

        async_executor = AsyncioExecutor()

        # 3. Create VLLMAgent if tools enabled
        vllm_agent = None
        if enable_tools:
            if workspace_path is None:
                raise ValueError(
                    "enable_tools=True requires workspace_path to be set"
                )
            
            # Lazy import to avoid coupling with agent bounded context
            try:
                from core.agents_and_tools.agents import VLLMAgent
                from core.agents_and_tools.agents.domain import AgentInitializationConfig
            except ImportError as e:
                raise ValueError(
                    "enable_tools=True requires VLLMAgent, but it's not available. "
                    "Install core.agents package."
                ) from e

            # Create AgentInitializationConfig (agent domain entity)
            # This keeps initialization logic in the agent's bounded context
            agent_config = AgentInitializationConfig(
                agent_id=agent_id,
                role=role,
                workspace_path=Path(workspace_path),
                vllm_url=vllm_url,
                enable_tools=enable_tools,
                audit_callback=None,  # Can be extended in the future
            )

            # Initialize VLLMAgent with config (agent knows how to initialize itself)
            vllm_agent = VLLMAgent(config=agent_config)

            logger.info(
                f"VLLMAgent created for {agent_id} with workspace {workspace_path}"
            )

        # 4. Create and return RayAgentExecutor with injected dependencies
        return RayAgentExecutor(
            config=config,
            publisher=publisher,
            vllm_client=vllm_client,
            async_executor=async_executor,
            vllm_agent=vllm_agent,
        )

