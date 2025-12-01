"""
Planning Service - gRPC Server
User Story Management with FSM and Decision Approval Workflow
"""

import asyncio
import logging
from concurrent import futures

import grpc
from nats.aio.client import Client as NATS
from planning.application.usecases import (
    ApproveDecisionUseCase,
    CreateStoryUseCase,
    ListStoriesUseCase,
    RejectDecisionUseCase,
    TransitionStoryUseCase,
)
from planning.application.usecases.create_epic_usecase import CreateEpicUseCase
from planning.application.usecases.create_project_usecase import CreateProjectUseCase
from planning.application.usecases.create_task_usecase import CreateTaskUseCase
from planning.application.usecases.get_epic_usecase import GetEpicUseCase
from planning.application.usecases.get_project_usecase import GetProjectUseCase
from planning.application.usecases.get_story_usecase import GetStoryUseCase
from planning.application.usecases.get_task_usecase import GetTaskUseCase
from planning.application.usecases.list_epics_usecase import ListEpicsUseCase
from planning.application.usecases.list_projects_usecase import ListProjectsUseCase
from planning.application.usecases.list_tasks_usecase import ListTasksUseCase
from planning.application.services.task_derivation_result_service import (
    TaskDerivationResultService,
)
from planning.gen import planning_pb2_grpc
from planning.infrastructure.adapters import (
    NATSMessagingAdapter,
    Neo4jConfig,
    StorageAdapter,
    ValkeyConfig,
)
from planning.infrastructure.adapters.environment_config_adapter import (
    EnvironmentConfigurationAdapter,
)
from planning.infrastructure.consumers.task_derivation_result_consumer import (
    TaskDerivationResultConsumer,
)

# Import refactored handlers (functions, not classes)
from planning.infrastructure.grpc.handlers import (
    approve_decision_handler,
    create_epic_handler,
    create_project_handler,
    create_story_handler,
    create_task_handler,
    get_epic_handler,
    get_project_handler,
    get_story_handler,
    get_task_handler,
    list_epics_handler,
    list_projects_handler,
    list_stories_handler,
    list_tasks_handler,
    reject_decision_handler,
    transition_story_handler,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class PlanningServiceServicer(planning_pb2_grpc.PlanningServiceServicer):
    """gRPC servicer for Planning Service."""

    # pylint: disable=too-many-arguments
    # NOSONAR S107 - Architecture decision: 15 use cases required for complete hierarchy
    # This exceeds the 13-parameter limit but is intentional for dependency injection clarity.
    # All 15 use cases (Project→Epic→Story→Task) are injected explicitly for maintainability.
    def __init__(
        self,
        # Project use cases
        create_project_uc: CreateProjectUseCase,
        get_project_uc: GetProjectUseCase,
        list_projects_uc: ListProjectsUseCase,
        # Epic use cases
        create_epic_uc: CreateEpicUseCase,
        get_epic_uc: GetEpicUseCase,
        list_epics_uc: ListEpicsUseCase,
        # Story use cases
        create_story_uc: CreateStoryUseCase,
        get_story_uc: GetStoryUseCase,
        list_stories_uc: ListStoriesUseCase,
        transition_story_uc: TransitionStoryUseCase,
        # Task use cases
        create_task_uc: CreateTaskUseCase,
        get_task_uc: GetTaskUseCase,
        list_tasks_uc: ListTasksUseCase,
        # Decision use cases
        approve_decision_uc: ApproveDecisionUseCase,
        reject_decision_uc: RejectDecisionUseCase,
    ):
        """Initialize servicer with use cases (Dependency Injection)."""
        # Project
        self.create_project_uc = create_project_uc
        self.get_project_uc = get_project_uc
        self.list_projects_uc = list_projects_uc
        # Epic
        self.create_epic_uc = create_epic_uc
        self.get_epic_uc = get_epic_uc
        self.list_epics_uc = list_epics_uc
        # Story
        self.create_story_uc = create_story_uc
        self.get_story_uc = get_story_uc
        self.list_stories_uc = list_stories_uc
        self.transition_story_uc = transition_story_uc
        # Task
        self.create_task_uc = create_task_uc
        self.get_task_uc = get_task_uc
        self.list_tasks_uc = list_tasks_uc
        # Decision
        self.approve_decision_uc = approve_decision_uc
        self.reject_decision_uc = reject_decision_uc

        logger.info("Planning Service servicer initialized with 15 use cases")

    # ========== Project Management (Root of Hierarchy) ==========

    async def CreateProject(self, request, context):
        """Create a new project (root of hierarchy)."""
        return await create_project_handler(request, context, self.create_project_uc)

    async def GetProject(self, request, context):
        """Get a single project by ID."""
        return await get_project_handler(request, context, self.get_project_uc)

    async def ListProjects(self, request, context):
        """List all projects."""
        return await list_projects_handler(request, context, self.list_projects_uc)

    # ========== Epic Management (Groups Stories) ==========

    async def CreateEpic(self, request, context):
        """Create a new epic under a project."""
        return await create_epic_handler(request, context, self.create_epic_uc)

    async def GetEpic(self, request, context):
        """Get a single epic by ID."""
        return await get_epic_handler(request, context, self.get_epic_uc)

    async def ListEpics(self, request, context):
        """List epics for a project."""
        return await list_epics_handler(request, context, self.list_epics_uc)

    # ========== Story Management (User Stories) ==========

    async def CreateStory(self, request, context):
        """Create a new user story."""
        return await create_story_handler(request, context, self.create_story_uc)

    async def ListStories(self, request, context):
        """List stories with optional filtering."""
        return await list_stories_handler(request, context, self.list_stories_uc)

    async def TransitionStory(self, request, context):
        """Transition story to a new state."""
        return await transition_story_handler(request, context, self.transition_story_uc)

    async def ApproveDecision(self, request, context):
        """Approve a decision for a story."""
        return await approve_decision_handler(request, context, self.approve_decision_uc)

    async def RejectDecision(self, request, context):
        """Reject a decision for a story."""
        return await reject_decision_handler(request, context, self.reject_decision_uc)

    async def GetStory(self, request, context):
        """Get a single story by ID."""
        return await get_story_handler(request, context, self.get_story_uc)

    # ========== Task Management (Atomic Work Items) ==========

    async def CreateTask(self, request, context):
        """Create a new task within a plan."""
        return await create_task_handler(request, context, self.create_task_uc)

    async def GetTask(self, request, context):
        """Get a single task by ID."""
        return await get_task_handler(request, context, self.get_task_uc)

    async def ListTasks(self, request, context):
        """List tasks for a story or plan."""
        return await list_tasks_handler(request, context, self.list_tasks_uc)


async def main():
    """Initialize and run Planning Service."""
    # Load configuration via adapter (Hexagonal Architecture)
    config = EnvironmentConfigurationAdapter()

    grpc_port = config.get_grpc_port()
    nats_url = config.get_nats_url()

    logger.info(f"Starting Planning Service on port {grpc_port}")
    logger.info(
        f"Neo4j: {config.get_neo4j_uri()}, "
        f"Valkey: {config.get_valkey_host()}:{config.get_valkey_port()}, "
        f"NATS: {nats_url}"
    )

    # Initialize NATS connection
    nc = NATS()
    await nc.connect(nats_url)
    js = nc.jetstream()
    logger.info("Connected to NATS JetStream")

    # Initialize adapters with config from environment adapter
    neo4j_config = Neo4jConfig(
        uri=config.get_neo4j_uri(),
        user=config.get_neo4j_user(),
        password=config.get_neo4j_password(),
        database=config.get_neo4j_database(),
    )

    valkey_config = ValkeyConfig(
        host=config.get_valkey_host(),
        port=config.get_valkey_port(),
        db=config.get_valkey_db(),
    )

    storage = StorageAdapter(
        neo4j_config=neo4j_config,
        valkey_config=valkey_config,
    )

    messaging = NATSMessagingAdapter(nats_client=nc, jetstream=js)

    # Initialize ALL use cases (15 total for complete hierarchy)
    # Project (3)
    create_project_uc = CreateProjectUseCase(storage=storage, messaging=messaging)
    get_project_uc = GetProjectUseCase(storage=storage)
    list_projects_uc = ListProjectsUseCase(storage=storage)
    # Epic (3)
    create_epic_uc = CreateEpicUseCase(storage=storage, messaging=messaging)
    get_epic_uc = GetEpicUseCase(storage=storage)
    list_epics_uc = ListEpicsUseCase(storage=storage)
    # Story (4)
    create_story_uc = CreateStoryUseCase(storage=storage, messaging=messaging)
    get_story_uc = GetStoryUseCase(storage=storage)
    list_stories_uc = ListStoriesUseCase(storage=storage)
    transition_story_uc = TransitionStoryUseCase(storage=storage, messaging=messaging)
    # Task (3)
    create_task_uc = CreateTaskUseCase(storage=storage, messaging=messaging)
    get_task_uc = GetTaskUseCase(storage=storage)
    list_tasks_uc = ListTasksUseCase(storage=storage)
    # Decision (2)
    approve_decision_uc = ApproveDecisionUseCase(messaging=messaging)
    reject_decision_uc = RejectDecisionUseCase(messaging=messaging)

    logger.info("✓ 15 use cases initialized (Project→Epic→Story→Task hierarchy)")

    # Initialize Task Derivation Result Service and Consumer
    task_derivation_service = TaskDerivationResultService(
        create_task_usecase=create_task_uc,
        storage=storage,
        messaging=messaging,
    )

    task_derivation_consumer = TaskDerivationResultConsumer(
        nats_client=nc,
        jetstream=js,
        task_derivation_service=task_derivation_service,
    )

    # Start consumer in background
    await task_derivation_consumer.start()
    logger.info("✓ TaskDerivationResultConsumer started (listening to agent.response.completed)")

    # Create gRPC server
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))

    planning_pb2_grpc.add_PlanningServiceServicer_to_server(
        PlanningServiceServicer(
            # Project
            create_project_uc=create_project_uc,
            get_project_uc=get_project_uc,
            list_projects_uc=list_projects_uc,
            # Epic
            create_epic_uc=create_epic_uc,
            get_epic_uc=get_epic_uc,
            list_epics_uc=list_epics_uc,
            # Story
            create_story_uc=create_story_uc,
            get_story_uc=get_story_uc,
            list_stories_uc=list_stories_uc,
            transition_story_uc=transition_story_uc,
            # Task
            create_task_uc=create_task_uc,
            get_task_uc=get_task_uc,
            list_tasks_uc=list_tasks_uc,
            # Decision
            approve_decision_uc=approve_decision_uc,
            reject_decision_uc=reject_decision_uc,
        ),
        server,
    )

    server.add_insecure_port(f"[::]:{grpc_port}")

    await server.start()
    logger.info(f"✓ Planning Service started on port {grpc_port}")

    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down Planning Service...")

        # Stop consumers
        await task_derivation_consumer.stop()
        logger.info("✓ TaskDerivationResultConsumer stopped")

        # Stop gRPC server
        await server.stop(grace=5)
        logger.info("✓ gRPC server stopped")

        # Close connections
        await nc.close()
        storage.close()
        logger.info("✓ Connections closed")

        logger.info("✓ Planning Service stopped gracefully")


if __name__ == "__main__":
    asyncio.run(main())

