"""Ray agent executor - infrastructure adapter for Ray cluster."""

import logging
from typing import Any

from ...application import ExecuteAgentTask
from ...domain import AgentConfig, ExecutionRequest
from ...domain.ports import IAsyncExecutor, IResultPublisher, IVLLMClient

logger = logging.getLogger(__name__)

# Import Ray if available
try:
    import ray
    if not hasattr(ray, 'remote'):
        raise ImportError("ray.remote not available")
    RAY_AVAILABLE = True
except (ImportError, AttributeError):
    RAY_AVAILABLE = False
    ray = None  # type: ignore


class RayAgentExecutor:
    """
    Executor para agentes en Ray cluster.

    Responsabilidad: Adapter de Ray (sync wrapper para Ray workers).

    Este es un THIN WRAPPER que:
    - Acepta parámetros sync (requerido por Ray)
    - Inyecta dependencias al use case
    - Delega toda la lógica a ExecuteAgentTask
    - Retorna resultado sync

    NO maneja:
    - Herramientas (responsabilidad de VLLMAgent)
    - Publicación NATS (responsabilidad de ExecuteAgentTask)
    - Timing/métricas (responsabilidad de ExecuteAgentTask)
    """

    def __init__(
        self,
        config: AgentConfig,
        publisher: IResultPublisher | None = None,
        vllm_client: IVLLMClient | None = None,
        async_executor: IAsyncExecutor | None = None,
        vllm_agent: Any | None = None,
    ):
        """
        Initialize Ray agent executor.

        Args:
            config: Configuración del agente (domain model)
            publisher: Puerto para publicar resultados (NATS, Kafka, etc.) - optional, will be recreated if None
            vllm_client: Puerto para cliente vLLM (text generation) - optional, will be recreated if None
            async_executor: Puerto para ejecutar código async (asyncio, trio, etc.) - optional, will be recreated if None
            vllm_agent: VLLMAgent instance (optional, for tool execution)

        Note:
            If publisher, vllm_client, or async_executor are None, they will be recreated
            in the worker to avoid serialization issues with dependencies that have
            problematic imports (e.g., nats).
        """
        logger.info(f"[RayAgentExecutor.__init__] Starting initialization for agent {config.agent_id}")
        logger.info(f"[RayAgentExecutor.__init__] Config: agent_id={config.agent_id}, role={config.role}, model={config.model}")
        logger.info(f"[RayAgentExecutor.__init__] Dependencies provided: publisher={publisher is not None}, vllm_client={vllm_client is not None}, async_executor={async_executor is not None}")

        import os
        import sys
        logger.info(f"[RayAgentExecutor.__init__] Environment: CWD={os.getcwd()}, PYTHONPATH={os.getenv('PYTHONPATH')}")
        logger.info(f"[RayAgentExecutor.__init__] sys.path (first 5): {sys.path[:5]}")

        self.config = config

        # Recreate dependencies in worker if not provided (avoids serialization issues)
        if publisher is None:
            logger.info("[RayAgentExecutor.__init__] Recreating NATSResultPublisher...")
            logger.info(f"[RayAgentExecutor.__init__] config.nats_url = {config.nats_url!r}")
            try:
                from .nats_result_publisher import NATSResultPublisher
                logger.info("[RayAgentExecutor.__init__] NATSResultPublisher imported successfully")
                publisher = NATSResultPublisher(config.nats_url)
                logger.info(f"[RayAgentExecutor.__init__] NATSResultPublisher created successfully with nats_url={config.nats_url!r}")
            except Exception as e:
                logger.error(f"[RayAgentExecutor.__init__] Failed to create NATSResultPublisher: {e}", exc_info=True)
                raise

        if vllm_client is None:
            logger.info("[RayAgentExecutor.__init__] Recreating VLLMHTTPClient...")
            try:
                from .vllm_http_client import VLLMHTTPClient
                logger.info("[RayAgentExecutor.__init__] VLLMHTTPClient imported successfully")
                role_str = config.role.value if hasattr(config.role, 'value') else str(config.role)
                vllm_client = VLLMHTTPClient(
                    vllm_url=config.vllm_url,
                    agent_id=config.agent_id,
                    role=role_str,
                    model=config.model,
                    timeout=config.timeout,
                )
                logger.info("[RayAgentExecutor.__init__] VLLMHTTPClient created successfully")
            except Exception as e:
                logger.error(f"[RayAgentExecutor.__init__] Failed to create VLLMHTTPClient: {e}", exc_info=True)
                raise

        if async_executor is None:
            logger.info("[RayAgentExecutor.__init__] Recreating AsyncioExecutor...")
            try:
                from .asyncio_executor import AsyncioExecutor
                logger.info("[RayAgentExecutor.__init__] AsyncioExecutor imported successfully")
                async_executor = AsyncioExecutor()
                logger.info("[RayAgentExecutor.__init__] AsyncioExecutor created successfully")
            except Exception as e:
                logger.error(f"[RayAgentExecutor.__init__] Failed to create AsyncioExecutor: {e}", exc_info=True)
                raise

        self.publisher = publisher
        self.vllm_client = vllm_client
        self.async_executor = async_executor
        self.vllm_agent = vllm_agent

        logger.info(
            f"[RayAgentExecutor.__init__] ✅ RayAgentExecutor initialized: {config.agent_id} ({config.role}) "
            f"using model {config.model} at {config.vllm_url} "
            f"[tools={'enabled' if config.enable_tools else 'disabled'}]"
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

        This is a sync wrapper that delegates to ExecuteAgentTask use case.

        Args:
            task_id: Unique task identifier
            task_description: Description of the task to solve
            constraints: Task constraints (rubric, requirements, etc.)
            diversity: Whether to increase diversity in the response

        Returns:
            Result dictionary with proposal/operations and metadata
        """
        logger.info(f"[RayAgentExecutor.run] Starting execution for task {task_id}, agent {self.config.agent_id}")
        logger.info(f"[RayAgentExecutor.run] Task description: {task_description[:100]}...")
        logger.info(f"[RayAgentExecutor.run] Constraints: {constraints}")

        try:
            # 1. Create domain request object
            logger.info("[RayAgentExecutor.run] Creating ExecutionRequest...")
            request = ExecutionRequest.create(
                task_id=task_id,
                task_description=task_description,
                constraints=constraints,
                diversity=diversity,
            )
            logger.info("[RayAgentExecutor.run] ExecutionRequest created successfully")

            # 2. Create use case (dependencies already injected in constructor)
            logger.info("[RayAgentExecutor.run] Creating ExecuteAgentTask use case...")
            use_case = ExecuteAgentTask(
                config=self.config,
                publisher=self.publisher,
                vllm_client=self.vllm_client,
                vllm_agent=self.vllm_agent,
            )
            logger.info("[RayAgentExecutor.run] ExecuteAgentTask created successfully")

            # 3. Execute async using injected executor
            logger.info("[RayAgentExecutor.run] Executing use case...")
            result = self.async_executor.run(use_case.execute(request))
            logger.info(f"[RayAgentExecutor.run] ✅ Execution completed successfully for task {task_id}")
            return result
        except Exception as e:
            logger.error(f"[RayAgentExecutor.run] ❌ Execution failed for task {task_id}: {e}", exc_info=True)
            raise

    def get_info(self) -> dict[str, Any]:
        """
        Get information about this agent job.

        Uses domain model AgentConfig for serialization.

        Returns:
            Dictionary with agent information
        """
        return self.config.to_dict()


__all__ = ["RayAgentExecutor"]

