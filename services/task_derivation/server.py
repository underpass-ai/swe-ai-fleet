"""Task Derivation Service - Event-Driven Worker.

Worker microservice that listens to NATS events and orchestrates task derivation:
1. Listens to `task.derivation.requested` events
2. Fetches plan/context, builds prompt, submits to Ray Executor
3. Listens to `agent.response.completed` events
4. Parses LLM response, creates tasks in Planning Service

Following Hexagonal Architecture with Dependency Injection.
"""

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

import nats
import yaml

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.shared.domain.value_objects.task_derivation.config.task_derivation_config import (
    TaskDerivationConfig,
)
from task_derivation.application.usecases.derive_tasks_usecase import (
    DeriveTasksUseCase,
)
from task_derivation.application.usecases.process_task_derivation_result_usecase import (
    ProcessTaskDerivationResultUseCase,
)
from task_derivation.infrastructure.adapters.context_service_adapter import (
    ContextServiceAdapter,
)
from task_derivation.infrastructure.adapters.nats_messaging_adapter import (
    NATSMessagingAdapter,
)
from task_derivation.infrastructure.adapters.planning_service_adapter import (
    PlanningServiceAdapter,
)
from task_derivation.infrastructure.adapters.ray_executor_adapter import (
    RayExecutorAdapter,
)
from task_derivation.infrastructure.consumers.task_derivation_request_consumer import (
    TaskDerivationRequestConsumer,
)
from task_derivation.infrastructure.consumers.task_derivation_result_consumer import (
    TaskDerivationResultConsumer,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class TaskDerivationServer:
    """Task Derivation Service server.

    Manages lifecycle of:
    - NATS connection
    - NATS consumers (task.derivation.requested, agent.response.completed)
    - gRPC adapters (Planning, Context, Ray Executor)

    Following Hexagonal Architecture:
    - Dependency injection at construction
    - Adapters implement ports
    - Use cases orchestrate domain logic
    """

    def __init__(self) -> None:
        """Initialize server (lazy initialization)."""
        self._nats_client = None
        self._jetstream = None
        self._request_consumer = None
        self._result_consumer = None
        self._shutdown_event = asyncio.Event()
        self._shutdown_task: asyncio.Task | None = None  # Track shutdown task to prevent GC

    async def start(self) -> None:
        """Start all server components."""
        logger.info("🚀 Starting Task Derivation Service...")

        # Load configuration
        config = self._load_configuration()

        # Initialize infrastructure
        await self._initialize_infrastructure(config)

        # Build dependency graph (DI)
        request_consumer, result_consumer = self._build_dependencies(config)

        # Start NATS consumers
        await request_consumer.start()
        self._request_consumer = request_consumer

        await result_consumer.start()
        self._result_consumer = result_consumer

        logger.info("✅ Task Derivation Service started successfully")
        logger.info(f"   NATS: {config.nats_url}")
        logger.info(f"   Planning Service: {config.planning_service_address}")
        logger.info(f"   Context Service: {config.context_service_address}")
        logger.info(f"   Ray Executor: {config.ray_executor_address}")
        logger.info("   Consumers: TaskDerivationRequest + TaskDerivationResult")

    async def wait_for_termination(self) -> None:
        """Wait until shutdown signal received."""
        await self._shutdown_event.wait()

    async def stop(self) -> None:
        """Stop all server components gracefully."""
        logger.info("🛑 Stopping Task Derivation Service...")

        # Stop NATS consumers
        if self._request_consumer:
            await self._request_consumer.stop()

        if self._result_consumer:
            await self._result_consumer.stop()

        # Close infrastructure connections
        if self._nats_client:
            await self._nats_client.close()

        logger.info("✅ Task Derivation Service stopped")

    def _load_configuration(self) -> "ServerConfiguration":  # noqa: F821
        """Load configuration from environment variables and YAML.

        Following Hexagonal Architecture:
        - Fail-fast on missing required config
        - Returns configuration object (not dict)

        Returns:
            ServerConfiguration (validated)
        """
        # NATS configuration
        nats_url = os.getenv("NATS_URL", "nats://nats.swe-ai-fleet.svc.cluster.local:4222")

        # gRPC service addresses
        planning_service_address = os.getenv(
            "PLANNING_SERVICE_ADDRESS",
            "planning.swe-ai-fleet.svc.cluster.local:50054",
        )
        context_service_address = os.getenv(
            "CONTEXT_SERVICE_ADDRESS",
            "context.swe-ai-fleet.svc.cluster.local:50054",
        )
        ray_executor_address = os.getenv(
            "RAY_EXECUTOR_ADDRESS",
            "ray-executor.swe-ai-fleet.svc.cluster.local:50057",
        )

        # vLLM configuration
        vllm_url = os.getenv("VLLM_URL", "http://vllm:8000")
        vllm_model = os.getenv("VLLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")

        # Task derivation configuration file
        config_path = os.getenv(
            "TASK_DERIVATION_CONFIG",
            "/app/config/task_derivation.yaml",
        )

        # Load YAML configuration (fail-fast if file not found)
        if not Path(config_path).exists():
            raise FileNotFoundError(
                f"Task derivation config file not found: {config_path}"
            )

        with open(config_path) as f:
            yaml_config = yaml.safe_load(f)

        # Extract prompt template and constraints
        prompt_template = yaml_config.get("prompt_template", "")
        if not prompt_template:
            raise ValueError("prompt_template is required in task_derivation.yaml")

        constraints = yaml_config.get("constraints", {})
        min_tasks = constraints.get("min_tasks", 3)
        max_tasks = constraints.get("max_tasks", 8)
        max_retries = yaml_config.get("retry", {}).get("max_retries", 3)

        # Create TaskDerivationConfig value object
        task_derivation_config = TaskDerivationConfig(
            prompt_template=prompt_template,
            min_tasks=min_tasks,
            max_tasks=max_tasks,
            max_retries=max_retries,
        )

        # Return configuration object
        return ServerConfiguration(
            nats_url=nats_url,
            planning_service_address=planning_service_address,
            context_service_address=context_service_address,
            ray_executor_address=ray_executor_address,
            vllm_url=vllm_url,
            vllm_model=vllm_model,
            task_derivation_config=task_derivation_config,
        )

    async def _initialize_infrastructure(
        self, config: "ServerConfiguration"  # noqa: F821
    ) -> None:
        """Initialize infrastructure connections.

        Args:
            config: Configuration object (validated)
        """
        logger.info("Initializing infrastructure connections...")

        # NATS
        self._nats_client = await nats.connect(config.nats_url)
        self._jetstream = self._nats_client.jetstream()
        logger.info(f"✅ NATS connected: {config.nats_url}")

    def _build_dependencies(
        self, config: "ServerConfiguration"  # noqa: F821
    ) -> tuple[TaskDerivationRequestConsumer, TaskDerivationResultConsumer]:
        """Build dependency graph using Dependency Injection.

        Following Hexagonal Architecture:
        - Adapters implement ports
        - Use cases receive ports via constructor
        - Consumers receive use cases via constructor

        Args:
            config: Configuration object

        Returns:
            Tuple of (request_consumer, result_consumer)
        """
        logger.info("Building dependency graph...")

        # Adapters (Infrastructure Layer)
        planning_adapter = PlanningServiceAdapter(
            address=config.planning_service_address,
        )
        context_adapter = ContextServiceAdapter(
            address=config.context_service_address,
        )
        ray_executor_adapter = RayExecutorAdapter(
            address=config.ray_executor_address,
            vllm_url=config.vllm_url,
            vllm_model=config.vllm_model,
        )
        messaging_adapter = NATSMessagingAdapter(
            nats_client=self._nats_client,
        )

        # Use Cases (Application Layer)
        derive_tasks_usecase = DeriveTasksUseCase(
            planning_port=planning_adapter,
            context_port=context_adapter,
            ray_executor_port=ray_executor_adapter,
            config=config.task_derivation_config,
        )

        process_result_usecase = ProcessTaskDerivationResultUseCase(
            planning_port=planning_adapter,
            messaging_port=messaging_adapter,
        )

        # Consumers (Infrastructure Layer - Inbound Adapters)
        request_consumer = TaskDerivationRequestConsumer(
            nats_client=self._nats_client,
            jetstream=self._jetstream,
            derive_tasks_usecase=derive_tasks_usecase,
        )

        result_consumer = TaskDerivationResultConsumer(
            nats_client=self._nats_client,
            jetstream=self._jetstream,
            process_usecase=process_result_usecase,
            messaging_port=messaging_adapter,
        )

        logger.info("✅ Dependency graph built")

        return request_consumer, result_consumer


class ServerConfiguration:
    """Server configuration DTO (immutable).

    Following Hexagonal Architecture:
    - DTO for configuration (not dict)
    - Immutable (frozen dataclass)
    - Fail-fast validation
    """

    def __init__(
        self,
        *,
        nats_url: str,
        planning_service_address: str,
        context_service_address: str,
        ray_executor_address: str,
        vllm_url: str,
        vllm_model: str,
        task_derivation_config: TaskDerivationConfig,
    ) -> None:
        """Initialize configuration.

        Args:
            nats_url: NATS server URL
            planning_service_address: Planning Service gRPC address
            context_service_address: Context Service gRPC address
            ray_executor_address: Ray Executor Service gRPC address
            vllm_url: vLLM service URL
            vllm_model: vLLM model name
            task_derivation_config: TaskDerivationConfig value object

        Raises:
            ValueError: If any required field is empty
        """
        if not nats_url or not nats_url.strip():
            raise ValueError("nats_url cannot be empty")
        if not planning_service_address or not planning_service_address.strip():
            raise ValueError("planning_service_address cannot be empty")
        if not context_service_address or not context_service_address.strip():
            raise ValueError("context_service_address cannot be empty")
        if not ray_executor_address or not ray_executor_address.strip():
            raise ValueError("ray_executor_address cannot be empty")
        if not vllm_url or not vllm_url.strip():
            raise ValueError("vllm_url cannot be empty")
        if not vllm_model or not vllm_model.strip():
            raise ValueError("vllm_model cannot be empty")

        self.nats_url = nats_url
        self.planning_service_address = planning_service_address
        self.context_service_address = context_service_address
        self.ray_executor_address = ray_executor_address
        self.vllm_url = vllm_url
        self.vllm_model = vllm_model
        self.task_derivation_config = task_derivation_config


async def serve() -> None:
    """Main server entrypoint."""
    server = TaskDerivationServer()

    # Setup signal handlers for graceful shutdown
    def signal_handler(signum: int, frame: object) -> None:
        logger.info(f"Received signal {signum}, initiating shutdown...")
        server._shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await server.start()
        await server.wait_for_termination()
    except Exception as exc:
        logger.exception("Fatal error in server: %s", exc)
        raise
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(serve())
