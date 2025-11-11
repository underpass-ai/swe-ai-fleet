"""
Planning Service - gRPC Server
User Story Management with FSM and Decision Approval Workflow
"""

import asyncio
import logging
from concurrent import futures

import grpc
from nats.aio.client import Client as NATS
from planning.gen import planning_pb2, planning_pb2_grpc

from planning.application.usecases import (
    ApproveDecisionUseCase,
    CreateStoryUseCase,
    InvalidTransitionError,
    ListStoriesUseCase,
    RejectDecisionUseCase,
    StoryNotFoundError,
    TransitionStoryUseCase,
)
from planning.application.usecases.create_epic_usecase import CreateEpicUseCase
from planning.application.usecases.create_project_usecase import CreateProjectUseCase
from planning.application.usecases.create_task_usecase import CreateTaskUseCase
from planning.application.usecases.derive_tasks_from_plan_usecase import (
    DeriveTasksFromPlanUseCase,
)
from planning.application.usecases.get_epic_usecase import GetEpicUseCase
from planning.application.usecases.get_project_usecase import GetProjectUseCase
from planning.application.usecases.get_task_usecase import GetTaskUseCase
from planning.application.usecases.list_epics_usecase import ListEpicsUseCase
from planning.application.usecases.list_projects_usecase import ListProjectsUseCase
from planning.application.usecases.list_tasks_usecase import ListTasksUseCase
from planning.application.services.task_derivation_result_service import (
    TaskDerivationResultService,
)
from planning.domain import StoryId, StoryState, StoryStateEnum
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.statuses.task_type import TaskType
from planning.infrastructure.adapters import (
    NATSMessagingAdapter,
    Neo4jConfig,
    StorageAdapter,
    ValkeyConfig,
)
from planning.infrastructure.adapters.environment_config_adapter import (
    EnvironmentConfigurationAdapter,
)
from planning.infrastructure.adapters.ray_executor_adapter import RayExecutorAdapter
from planning.infrastructure.consumers.plan_approved_consumer import (
    PlanApprovedConsumer,
)
from planning.infrastructure.consumers.task_derivation_result_consumer import (
    TaskDerivationResultConsumer,
)
from planning.infrastructure.mappers import (
    ResponseProtobufMapper,
    StoryProtobufMapper,
)

# Import refactored handlers (functions, not classes)
from planning.infrastructure.grpc.handlers import (
    create_project,
    get_project,
    list_projects,
    create_epic,
    get_epic,
    list_epics,
    create_story,
    get_story,
    list_stories,
    transition_story,
    create_task,
    get_task,
    list_tasks,
    approve_decision,
    reject_decision,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class PlanningServiceServicer(planning_pb2_grpc.PlanningServiceServicer):
    """gRPC servicer for Planning Service."""

    # pylint: disable=too-many-arguments
    # NOSONAR - 15 parameters needed for comprehensive use case injection
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
        list_stories_uc: ListStoriesUseCase,
        transition_story_uc: TransitionStoryUseCase,
        # Task use cases
        create_task_uc: CreateTaskUseCase,
        get_task_uc: GetTaskUseCase,
        list_tasks_uc: ListTasksUseCase,
        # Decision use cases
        approve_decision_uc: ApproveDecisionUseCase,
        reject_decision_uc: RejectDecisionUseCase,
        # Storage (for GetStory that doesn't have use case yet)
        storage: StorageAdapter,
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
        self.list_stories_uc = list_stories_uc
        self.transition_story_uc = transition_story_uc
        # Task
        self.create_task_uc = create_task_uc
        self.get_task_uc = get_task_uc
        self.list_tasks_uc = list_tasks_uc
        # Decision
        self.approve_decision_uc = approve_decision_uc
        self.reject_decision_uc = reject_decision_uc
        # Storage (temporary, for GetStory)
        self.storage = storage

        logger.info("Planning Service servicer initialized with 15 use cases")

    # ========== Project Management (Root of Hierarchy) ==========

    async def CreateProject(self, request, context):
        """Create a new project (root of hierarchy)."""
        return await create_project(request, context, self.create_project_uc)

    async def GetProject(self, request, context):
        """Get a single project by ID."""
        return await get_project(request, context, self.get_project_uc)

    async def ListProjects(self, request, context):
        """List all projects."""
        return await list_projects(request, context, self.list_projects_uc)

    # ========== Epic Management (Groups Stories) ==========

    async def CreateEpic(self, request, context):
        """Create a new epic under a project."""
        return await create_epic(request, context, self.create_epic_uc)

    async def GetEpic(self, request, context):
        """Get a single epic by ID."""
        return await get_epic(request, context, self.get_epic_uc)

    async def ListEpics(self, request, context):
        """List epics for a project."""
        return await list_epics(request, context, self.list_epics_uc)

    # ========== Story Management (User Stories) ==========

    async def CreateStory(self, request, context):
        """Create a new user story."""
        return await create_story(request, context, self.create_story_uc)

    async def ListStories(self, request, context):
        """List stories with optional filtering."""
        return await list_stories(request, context, self.list_stories_uc)

    async def TransitionStory(self, request, context):
        """Transition story to a new state."""
        return await transition_story(request, context, self.transition_story_uc)

    async def ApproveDecision(self, request, context):
        """Approve a decision for a story."""
        return await approve_decision(request, context, self.approve_decision_uc)

    async def RejectDecision(self, request, context):
        """Reject a decision for a story."""
        return await reject_decision(request, context, self.reject_decision_uc)

    async def GetStory(self, request, context):
        """Get a single story by ID."""
        return await get_story(request, context, self.storage)

    # ========== Task Management (Atomic Work Items) ==========

    async def CreateTask(self, request, context):
        """Create a new task within a plan."""
        return await create_task(request, context, self.create_task_uc)

    async def GetTask(self, request, context):
        """Get a single task by ID."""
        return await get_task(request, context, self.get_task_uc)

    async def ListTasks(self, request, context):
        """List tasks for a story or plan."""
        return await list_tasks(request, context, self.list_tasks_uc)


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
    # Story (3)
    create_story_uc = CreateStoryUseCase(storage=storage, messaging=messaging)
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

    # ========== Task Derivation (Ray Executor Integration) ==========

    # Ray Executor adapter (gRPC client)
    ray_executor_url = config.get_ray_executor_url()
    ray_executor_adapter = RayExecutorAdapter(
        ray_executor_url=ray_executor_url,
        vllm_url=config.get_vllm_url(),
        vllm_model=config.get_vllm_model(),
    )

    logger.info(f"✓ Ray Executor adapter initialized ({ray_executor_url})")

    # Task derivation use case
    derive_tasks_uc = DeriveTasksFromPlanUseCase(
        ray_executor=ray_executor_adapter,
        config=config,
    )

    # Task derivation application service
    task_derivation_service = TaskDerivationResultService(
        create_task_usecase=create_task_uc,
        storage=storage,
        messaging=messaging,
    )

    logger.info("✓ Task derivation components initialized")

    # ========== NATS Consumers (Event-Driven) ==========

    # Consumer: planning.plan.approved → DeriveTasksFromPlanUseCase
    plan_approved_consumer = PlanApprovedConsumer(
        nats_client=nc,
        jetstream=js,
        derive_tasks_usecase=derive_tasks_uc,
    )

    # Consumer: agent.response.completed → TaskDerivationResultService
    task_derivation_result_consumer = TaskDerivationResultConsumer(
        nats_client=nc,
        jetstream=js,
        task_derivation_service=task_derivation_service,
    )

    # Start consumers (background polling tasks)
    await plan_approved_consumer.start()
    await task_derivation_result_consumer.start()

    logger.info("✓ NATS consumers started (plan approved, task derivation results)")

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
            list_stories_uc=list_stories_uc,
            transition_story_uc=transition_story_uc,
            # Task
            create_task_uc=create_task_uc,
            get_task_uc=get_task_uc,
            list_tasks_uc=list_tasks_uc,
            # Decision
            approve_decision_uc=approve_decision_uc,
            reject_decision_uc=reject_decision_uc,
            # Storage (for GetStory temporary)
            storage=storage,
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

        # Graceful shutdown: stop consumers first
        await plan_approved_consumer.stop()
        await task_derivation_result_consumer.stop()
        logger.info("✓ NATS consumers stopped")

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

