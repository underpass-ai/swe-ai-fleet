"""Workflow Orchestration Service - gRPC Server.

RBAC Level 2: Workflow Action Control
Coordinates multi-role task execution workflows.

Following Hexagonal Architecture with Dependency Injection.
"""

import asyncio
import logging
import os
import signal
import sys
from concurrent import futures

import grpc
import nats
import valkey.asyncio as valkey  # Valkey is Redis-compatible, use redis client
import yaml
from neo4j import AsyncGraphDatabase

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from services.workflow.application.usecases.execute_workflow_action_usecase import (
    ExecuteWorkflowActionUseCase,
)
from services.workflow.application.usecases.get_pending_tasks_usecase import (
    GetPendingTasksUseCase,
)
from services.workflow.application.usecases.get_workflow_state_usecase import (
    GetWorkflowStateUseCase,
)
from services.workflow.application.usecases.initialize_task_workflow_usecase import (
    InitializeTaskWorkflowUseCase,
)
from services.workflow.domain.services.workflow_state_machine import WorkflowStateMachine
from services.workflow.domain.services.workflow_transition_rules import (
    WorkflowTransitionRules,
)

# Import generated protobuf code
from services.workflow.gen import workflow_pb2, workflow_pb2_grpc
from services.workflow.infrastructure.adapters.environment_configuration_adapter import (
    EnvironmentConfigurationAdapter,
)
from services.workflow.infrastructure.adapters.nats_messaging_adapter import (
    NatsMessagingAdapter,
)
from services.workflow.infrastructure.adapters.neo4j_workflow_adapter import (
    Neo4jWorkflowAdapter,
)
from services.workflow.infrastructure.adapters.valkey_workflow_cache_adapter import (
    ValkeyWorkflowCacheAdapter,
)
from services.workflow.infrastructure.consumers.agent_work_completed_consumer import (
    AgentWorkCompletedConsumer,
)
from services.workflow.infrastructure.consumers.planning_events_consumer import (
    PlanningEventsConsumer,
)
from services.workflow.infrastructure.dto.server_configuration_dto import (
    ServerConfigurationDTO,
)
from services.workflow.infrastructure.grpc_servicer import (
    WorkflowOrchestrationServicer,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class WorkflowOrchestrationServer:
    """Workflow Orchestration Service server.

    Manages lifecycle of:
    - gRPC server (port 50056)
    - NATS consumer (agent.work.completed)
    - Neo4j connection
    - Valkey cache

    Following Hexagonal Architecture:
    - Dependency injection at construction
    - Adapters implement ports
    - Use cases orchestrate domain logic
    """

    def __init__(self) -> None:
        """Initialize server (lazy initialization)."""
        self._grpc_server = None
        self._nats_client = None
        self._neo4j_driver = None
        self._valkey_client = None
        self._agent_work_consumer = None
        self._planning_consumer = None
        self._shutdown_event = asyncio.Event()
        self._shutdown_task: asyncio.Task | None = None  # Track shutdown task to prevent GC

    async def start(self) -> None:
        """Start all server components."""
        logger.info("🚀 Starting Workflow Orchestration Service...")

        # Load configuration
        config = self._load_configuration()

        # Initialize infrastructure
        await self._initialize_infrastructure(config)

        # Build dependency graph (DI)
        servicer, agent_consumer, planning_consumer = self._build_dependencies(config)

        # Start gRPC server
        await self._start_grpc_server(servicer, config.grpc_port)

        # Start NATS consumers
        await agent_consumer.start()
        self._agent_work_consumer = agent_consumer

        await planning_consumer.start()
        self._planning_consumer = planning_consumer

        logger.info("✅ Workflow Orchestration Service started successfully")
        logger.info(f"   gRPC port: {config.grpc_port}")
        logger.info(f"   Neo4j: {config.neo4j_uri}")
        logger.info(f"   Valkey: {config.valkey_host}:{config.valkey_port}")
        logger.info(f"   NATS: {config.nats_url}")
        logger.info("   Consumers: AgentWorkCompleted + PlanningEvents")

    async def wait_for_termination(self) -> None:
        """Wait until shutdown signal received."""
        await self._shutdown_event.wait()

    async def stop(self) -> None:
        """Stop all server components gracefully."""
        logger.info("🛑 Stopping Workflow Orchestration Service...")

        # Stop NATS consumers
        if self._agent_work_consumer:
            await self._agent_work_consumer.stop()

        if self._planning_consumer:
            await self._planning_consumer.stop()

        # Stop gRPC server
        if self._grpc_server:
            await self._grpc_server.stop(grace=5)

        # Close infrastructure connections
        if self._nats_client:
            await self._nats_client.close()

        if self._neo4j_driver:
            await self._neo4j_driver.close()

        if self._valkey_client:
            await self._valkey_client.aclose()

        logger.info("✅ Workflow Orchestration Service stopped")

    def _load_configuration(self) -> ServerConfigurationDTO:
        """Load configuration using ConfigurationPort adapter.

        Following Hexagonal Architecture:
        - Uses ConfigurationPort (not os.getenv directly)
        - Returns DTO (not dict)
        - Fail-fast on missing required config

        Returns:
            ServerConfigurationDTO (validated)
        """
        # Configuration adapter (Hexagonal Architecture)
        config_adapter = EnvironmentConfigurationAdapter()

        # gRPC configuration
        grpc_port = config_adapter.get_int("GRPC_PORT", default=50056)

        # Neo4j configuration (fail-fast if password missing)
        neo4j_uri = config_adapter.get_config_value("NEO4J_URI", "bolt://neo4j:7687")
        neo4j_user = config_adapter.get_config_value("NEO4J_USER", "neo4j")
        neo4j_password = config_adapter.get_config_value("NEO4J_PASSWORD")  # No default = fail-fast

        # Valkey configuration
        valkey_host = config_adapter.get_config_value("VALKEY_HOST", "valkey")
        valkey_port = config_adapter.get_int("VALKEY_PORT", default=6379)

        # NATS configuration
        nats_url = config_adapter.get_config_value("NATS_URL", "nats://nats:4222")

        # FSM configuration file
        fsm_config_path = config_adapter.get_config_value(
            "WORKFLOW_FSM_CONFIG",
            "/app/config/workflow.fsm.yaml"
        )

        # Load FSM configuration (fail-fast if file not found)
        with open(fsm_config_path) as f:
            fsm_config = yaml.safe_load(f)

        # Return DTO (validates configuration)
        return ServerConfigurationDTO(
            grpc_port=grpc_port,
            neo4j_uri=neo4j_uri,
            neo4j_user=neo4j_user,
            neo4j_password=neo4j_password,
            valkey_host=valkey_host,
            valkey_port=valkey_port,
            nats_url=nats_url,
            fsm_config=fsm_config,
        )

    async def _initialize_infrastructure(self, config: ServerConfigurationDTO) -> None:
        """Initialize infrastructure connections.

        Args:
            config: Configuration DTO (validated)
        """
        logger.info("Initializing infrastructure connections...")

        # Neo4j
        self._neo4j_driver = AsyncGraphDatabase.driver(
            config.neo4j_uri,
            auth=(config.neo4j_user, config.neo4j_password),
        )
        logger.info(f"✅ Neo4j connected: {config.neo4j_uri}")

        # Valkey
        self._valkey_client = valkey.Valkey(
            host=config.valkey_host,
            port=config.valkey_port,
            decode_responses=False,  # We handle encoding
        )
        await self._valkey_client.ping()
        logger.info(f"✅ Valkey connected: {config.valkey_host}:{config.valkey_port}")

        # NATS
        self._nats_client = await nats.connect(config.nats_url)
        logger.info(f"✅ NATS connected: {config.nats_url}")

    def _build_dependencies(self, config: ServerConfigurationDTO) -> tuple:  # noqa: PLR0914
        """Build dependency graph using Dependency Injection.

        Following Hexagonal Architecture:
        - Domain services (FSM)
        - Adapters (Neo4j, Valkey, NATS)
        - Use cases (injected with ports)
        - Servicer (injected with use cases)

        Args:
            config: Configuration DTO (validated)

        Returns:
            Tuple of (servicer, agent_consumer, planning_consumer)
        """
        logger.info("Building dependency graph...")

        # Domain services
        transition_rules = WorkflowTransitionRules(config.fsm_config)
        state_machine = WorkflowStateMachine(transition_rules)

        # Infrastructure adapters
        neo4j_adapter = Neo4jWorkflowAdapter(self._neo4j_driver)

        # Valkey cache (decorates Neo4j)
        repository = ValkeyWorkflowCacheAdapter(
            valkey_client=self._valkey_client,
            primary_repository=neo4j_adapter,
            ttl_seconds=3600,  # 1 hour cache
        )

        # NATS messaging
        jetstream = self._nats_client.jetstream()
        messaging = NatsMessagingAdapter(
            nats_client=self._nats_client,
            jetstream=jetstream,
        )

        # Application use cases (dependency injection)
        get_workflow_state = GetWorkflowStateUseCase(repository=repository)

        execute_workflow_action = ExecuteWorkflowActionUseCase(
            repository=repository,
            messaging=messaging,
            state_machine=state_machine,
        )

        get_pending_tasks = GetPendingTasksUseCase(repository=repository)

        initialize_task_workflow = InitializeTaskWorkflowUseCase(
            repository=repository,
            messaging=messaging,
        )

        # gRPC servicer (dependency injection)
        servicer = WorkflowOrchestrationServicer(
            get_workflow_state=get_workflow_state,
            execute_workflow_action=execute_workflow_action,
            get_pending_tasks=get_pending_tasks,
            workflow_pb2=workflow_pb2,
            workflow_pb2_grpc=workflow_pb2_grpc,
        )

        # NATS consumers (dependency injection)
        agent_work_consumer = AgentWorkCompletedConsumer(
            nats_client=self._nats_client,
            jetstream=jetstream,
            execute_workflow_action=execute_workflow_action,
        )

        planning_consumer = PlanningEventsConsumer(
            nats_client=self._nats_client,
            jetstream=jetstream,
            initialize_task_workflow=initialize_task_workflow,
        )

        logger.info("✅ Dependency graph built")

        return servicer, agent_work_consumer, planning_consumer

    async def _start_grpc_server(self, servicer, port: int) -> None:
        """Start gRPC server.

        Args:
            servicer: gRPC servicer instance
            port: Port number
        """
        self._grpc_server = grpc.aio.server(
            futures.ThreadPoolExecutor(max_workers=10)
        )

        workflow_pb2_grpc.add_WorkflowOrchestrationServiceServicer_to_server(
            servicer,
            self._grpc_server,
        )

        self._grpc_server.add_insecure_port(f"[::]:{port}")
        await self._grpc_server.start()

        logger.info(f"✅ gRPC server listening on port {port}")


async def main() -> None:
    """Main entry point."""
    server = WorkflowOrchestrationServer()

    # Setup signal handlers
    loop = asyncio.get_event_loop()

    def signal_handler():
        logger.info("Received shutdown signal")
        # Save task reference to prevent GC (SonarQube: asyncio best practice)
        shutdown_task = asyncio.create_task(server.stop())
        server._shutdown_event.set()
        # Keep reference to ensure task completes
        server._shutdown_task = shutdown_task

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    try:
        await server.start()
        await server.wait_for_termination()

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        await server.stop()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

