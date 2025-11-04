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
        publisher: IResultPublisher,
        vllm_client: IVLLMClient,
        async_executor: IAsyncExecutor,
        vllm_agent: Any | None = None,
    ):
        """
        Initialize Ray agent executor.

        Args:
            config: Configuración del agente (domain model)
            publisher: Puerto para publicar resultados (NATS, Kafka, etc.)
            vllm_client: Puerto para cliente vLLM (text generation)
            async_executor: Puerto para ejecutar código async (asyncio, trio, etc.)
            vllm_agent: VLLMAgent instance (optional, for tool execution)
        """
        self.config = config
        self.publisher = publisher
        self.vllm_client = vllm_client
        self.async_executor = async_executor
        self.vllm_agent = vllm_agent

        logger.info(
            f"RayAgentExecutor initialized: {config.agent_id} ({config.role}) "
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
        # 1. Create domain request object
        request = ExecutionRequest.create(
            task_id=task_id,
            task_description=task_description,
            constraints=constraints,
            diversity=diversity,
        )

        # 2. Create use case (dependencies already injected in constructor)
        use_case = ExecuteAgentTask(
            config=self.config,
            publisher=self.publisher,
            vllm_client=self.vllm_client,
            vllm_agent=self.vllm_agent,
        )

        # 3. Execute async using injected executor
        return self.async_executor.run(use_case.execute(request))

    def get_info(self) -> dict[str, Any]:
        """
        Get information about this agent job.

        Uses domain model AgentConfig for serialization.

        Returns:
            Dictionary with agent information
        """
        return self.config.to_dict()


__all__ = ["RayAgentExecutor"]

