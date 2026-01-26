"""
Planning Service - gRPC Server
User Story Management with FSM and Decision Approval Workflow
"""

import asyncio
import logging
import os
from concurrent import futures

import grpc
from nats.aio.client import Client as NATS
from planning.application.services.dual_write_reconciliation_service import (
    DualWriteReconciliationService,
)
from planning.application.services.task_derivation_result_service import (
    TaskDerivationResultService,
)
from planning.application.usecases import (
    AddStoriesToReviewUseCase,
    ApproveDecisionUseCase,
    ApproveReviewPlanUseCase,
    CancelBacklogReviewCeremonyUseCase,
    CompleteBacklogReviewCeremonyUseCase,
    CreateBacklogReviewCeremonyUseCase,
    CreateStoryUseCase,
    GetBacklogReviewCeremonyUseCase,
    ListBacklogReviewCeremoniesUseCase,
    ListStoriesUseCase,
    ProcessStoryReviewResultUseCase,
    RejectDecisionUseCase,
    RejectReviewPlanUseCase,
    RemoveStoryFromReviewUseCase,
    StartBacklogReviewCeremonyUseCase,
    StartPlanningCeremonyViaProcessorUseCase,
    TransitionStoryUseCase,
)
from planning.application.usecases.create_epic_usecase import CreateEpicUseCase
from planning.application.usecases.create_project_usecase import CreateProjectUseCase
from planning.application.usecases.create_task_usecase import CreateTaskUseCase
from planning.application.usecases.delete_epic_usecase import DeleteEpicUseCase
from planning.application.usecases.delete_project_usecase import DeleteProjectUseCase
from planning.application.usecases.delete_story_usecase import DeleteStoryUseCase
from planning.application.usecases.get_epic_usecase import GetEpicUseCase
from planning.application.usecases.get_project_usecase import GetProjectUseCase
from planning.application.usecases.get_story_usecase import GetStoryUseCase
from planning.application.usecases.get_task_usecase import GetTaskUseCase
from planning.application.usecases.list_epics_usecase import ListEpicsUseCase
from planning.application.usecases.list_projects_usecase import ListProjectsUseCase
from planning.application.usecases.list_tasks_usecase import ListTasksUseCase
from planning.gen import planning_pb2_grpc
from planning.infrastructure.adapters import (
    NATSMessagingAdapter,
    Neo4jConfig,
    ValkeyDualWriteLedgerAdapter,
    StorageAdapter,
    ValkeyConfig,
)
from planning.infrastructure.adapters.context_service_adapter import (
    ContextServiceAdapter,
)
from planning.infrastructure.adapters.environment_config_adapter import (
    EnvironmentConfigurationAdapter,
)
from planning.infrastructure.adapters.planning_ceremony_processor_adapter import (
    PlanningCeremonyProcessorAdapter,
)
from planning.infrastructure.adapters.ray_executor_adapter import (
    RayExecutorAdapter,
)
from planning.infrastructure.consumers.deliberations_complete_progress_consumer import (
    DeliberationsCompleteProgressConsumer,
)
from planning.infrastructure.consumers.dual_write_reconciler_consumer import (
    DualWriteReconcilerConsumer,
)
from planning.infrastructure.consumers.tasks_complete_progress_consumer import (
    TasksCompleteProgressConsumer,
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
    delete_epic_handler,
    delete_project_handler,
    delete_story_handler,
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

# Backlog Review Ceremony handlers (10)
from planning.infrastructure.grpc.handlers import (
    add_stories_to_review_handler,
    approve_review_plan_handler,
    cancel_backlog_review_ceremony_handler,
    complete_backlog_review_ceremony_handler,
    create_backlog_review_ceremony_handler,
    get_backlog_review_ceremony_handler,
    list_backlog_review_ceremonies_handler,
    reject_review_plan_handler,
    remove_story_from_review_handler,
    start_backlog_review_ceremony_handler,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class PlanningServiceServicer(planning_pb2_grpc.PlanningServiceServicer):
    """gRPC servicer for Planning Service."""

    # pylint: disable=too-many-arguments
    # NOSONAR S107 - Architecture decision: 27 use cases required for complete hierarchy + Backlog Review
    # This exceeds the 13-parameter limit but is intentional for dependency injection clarity.
    # All 27 use cases (Project→Epic→Story→Task + Backlog Review Ceremony) are injected explicitly for maintainability.
    def __init__(
        self,
        # Project use cases
        create_project_uc: CreateProjectUseCase,
        delete_project_uc: DeleteProjectUseCase,
        get_project_uc: GetProjectUseCase,
        list_projects_uc: ListProjectsUseCase,
        # Epic use cases
        create_epic_uc: CreateEpicUseCase,
        delete_epic_uc: DeleteEpicUseCase,
        get_epic_uc: GetEpicUseCase,
        list_epics_uc: ListEpicsUseCase,
        # Story use cases
        create_story_uc: CreateStoryUseCase,
        delete_story_uc: DeleteStoryUseCase,
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
        # Backlog Review Ceremony use cases
        create_backlog_review_ceremony_uc: CreateBacklogReviewCeremonyUseCase,
        get_backlog_review_ceremony_uc: GetBacklogReviewCeremonyUseCase,
        list_backlog_review_ceremonies_uc: ListBacklogReviewCeremoniesUseCase,
        add_stories_to_review_uc: AddStoriesToReviewUseCase,
        remove_story_from_review_uc: RemoveStoryFromReviewUseCase,
        start_backlog_review_ceremony_uc: StartBacklogReviewCeremonyUseCase,
        approve_review_plan_uc: ApproveReviewPlanUseCase,
        reject_review_plan_uc: RejectReviewPlanUseCase,
        complete_backlog_review_ceremony_uc: CompleteBacklogReviewCeremonyUseCase,
        cancel_backlog_review_ceremony_uc: CancelBacklogReviewCeremonyUseCase,
    ):
        """Initialize servicer with use cases (Dependency Injection)."""
        # Project
        self.create_project_uc = create_project_uc
        self.delete_project_uc = delete_project_uc
        self.get_project_uc = get_project_uc
        self.list_projects_uc = list_projects_uc
        # Epic
        self.create_epic_uc = create_epic_uc
        self.delete_epic_uc = delete_epic_uc
        self.get_epic_uc = get_epic_uc
        self.list_epics_uc = list_epics_uc
        # Story
        self.create_story_uc = create_story_uc
        self.delete_story_uc = delete_story_uc
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
        # Backlog Review Ceremony
        self.create_backlog_review_ceremony_uc = create_backlog_review_ceremony_uc
        self.get_backlog_review_ceremony_uc = get_backlog_review_ceremony_uc
        self.list_backlog_review_ceremonies_uc = list_backlog_review_ceremonies_uc
        self.add_stories_to_review_uc = add_stories_to_review_uc
        self.remove_story_from_review_uc = remove_story_from_review_uc
        self.start_backlog_review_ceremony_uc = start_backlog_review_ceremony_uc
        self.approve_review_plan_uc = approve_review_plan_uc
        self.reject_review_plan_uc = reject_review_plan_uc
        self.complete_backlog_review_ceremony_uc = complete_backlog_review_ceremony_uc
        self.cancel_backlog_review_ceremony_uc = cancel_backlog_review_ceremony_uc
        # ProcessStoryReviewResultUseCase for AddAgentDeliberation gRPC handler (set after initialization)
        self.process_story_review_result_uc: ProcessStoryReviewResultUseCase | None = None
        # StartPlanningCeremonyViaProcessorUseCase (thin client, set when PLANNING_CEREMONY_PROCESSOR_URL is set)
        self.planning_ceremony_processor_uc = None

        logger.info("Planning Service servicer initialized with 27 use cases")

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

    async def DeleteProject(self, request, context):
        """Delete a project by ID."""
        return await delete_project_handler(request, context, self.delete_project_uc)

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

    async def DeleteEpic(self, request, context):
        """Delete an epic by ID."""
        return await delete_epic_handler(request, context, self.delete_epic_uc)

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

    async def DeleteStory(self, request, context):
        """Delete a story by ID."""
        return await delete_story_handler(request, context, self.delete_story_uc)

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

    # ========== Backlog Review Ceremony (Multi-Council Story Review) ==========

    async def CreateBacklogReviewCeremony(self, request, context):
        """Create a new backlog review ceremony."""
        return await create_backlog_review_ceremony_handler(
            request, context, self.create_backlog_review_ceremony_uc
        )

    async def GetBacklogReviewCeremony(self, request, context):
        """Get a backlog review ceremony by ID."""
        return await get_backlog_review_ceremony_handler(
            request, context, self.get_backlog_review_ceremony_uc
        )

    async def ListBacklogReviewCeremonies(self, request, context):
        """List backlog review ceremonies with optional filtering."""
        return await list_backlog_review_ceremonies_handler(
            request, context, self.list_backlog_review_ceremonies_uc
        )

    async def AddStoriesToReview(self, request, context):
        """Add stories to a ceremony."""
        return await add_stories_to_review_handler(
            request, context, self.add_stories_to_review_uc
        )

    async def RemoveStoryFromReview(self, request, context):
        """Remove a story from a ceremony."""
        return await remove_story_from_review_handler(
            request, context, self.remove_story_from_review_uc
        )

    async def AddAgentDeliberation(self, request, context):
        """Add an agent deliberation to a ceremony."""
        from planning.infrastructure.grpc.handlers.add_agent_deliberation_handler import (
            add_agent_deliberation_handler,
        )
        return await add_agent_deliberation_handler(
            request, context, self.process_story_review_result_uc
        )

    async def StartBacklogReviewCeremony(self, request, context):
        """Start the backlog review ceremony (multi-council reviews)."""
        return await start_backlog_review_ceremony_handler(
            request,
            context,
            self.start_backlog_review_ceremony_uc,
            planning_ceremony_processor_uc=getattr(
                self, "planning_ceremony_processor_uc", None
            ),
        )

    async def ApproveReviewPlan(self, request, context):
        """Approve a review plan (PO approval)."""
        return await approve_review_plan_handler(
            request, context, self.approve_review_plan_uc
        )

    async def RejectReviewPlan(self, request, context):
        """Reject a review plan (PO rejection)."""
        return await reject_review_plan_handler(
            request, context, self.reject_review_plan_uc
        )

    async def CompleteBacklogReviewCeremony(self, request, context):
        """Complete the backlog review ceremony."""
        return await complete_backlog_review_ceremony_handler(
            request, context, self.complete_backlog_review_ceremony_uc
        )

    async def CancelBacklogReviewCeremony(self, request, context):
        """Cancel the backlog review ceremony."""
        return await cancel_backlog_review_ceremony_handler(
            request, context, self.cancel_backlog_review_ceremony_uc
        )


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

    # Initialize dual write ledger adapter
    dual_write_ledger = ValkeyDualWriteLedgerAdapter(config=valkey_config)
    logger.info("✓ Dual write ledger adapter initialized")

    messaging = NATSMessagingAdapter(nats_client=nc, jetstream=js)

    storage = StorageAdapter(
        neo4j_config=neo4j_config,
        valkey_config=valkey_config,
        dual_write_ledger=dual_write_ledger,
        messaging=messaging,
    )

    # Initialize ALL use cases (18 total for complete hierarchy)
    # Project (4)
    create_project_uc = CreateProjectUseCase(storage=storage, messaging=messaging)
    delete_project_uc = DeleteProjectUseCase(storage=storage)
    get_project_uc = GetProjectUseCase(storage=storage)
    list_projects_uc = ListProjectsUseCase(storage=storage)
    # Epic (4)
    create_epic_uc = CreateEpicUseCase(storage=storage, messaging=messaging)
    delete_epic_uc = DeleteEpicUseCase(storage=storage)
    get_epic_uc = GetEpicUseCase(storage=storage)
    list_epics_uc = ListEpicsUseCase(storage=storage)
    # Story (5)
    create_story_uc = CreateStoryUseCase(storage=storage, messaging=messaging)
    delete_story_uc = DeleteStoryUseCase(storage=storage)
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

    logger.info("✓ 18 use cases initialized (Project→Epic→Story→Task hierarchy)")

    # Initialize Ray Executor adapter for Backlog Review
    ray_executor_url = config.get_ray_executor_url()
    vllm_url = config.get_vllm_url()
    vllm_model = config.get_vllm_model()
    ray_executor_adapter = RayExecutorAdapter(
        grpc_address=ray_executor_url,
        vllm_url=vllm_url,
        vllm_model=vllm_model,
    )
    logger.info(f"✓ Ray Executor adapter initialized: {ray_executor_url}")

    # Initialize Context Service adapter for Backlog Review
    context_service_url = config.get_context_service_url()
    context_adapter = ContextServiceAdapter(
        grpc_address=context_service_url,
        timeout_seconds=10.0,  # 10 seconds timeout for context retrieval
    )
    logger.info(f"✓ Context Service adapter initialized: {context_service_url}")

    # Backlog Review Ceremony (9 use cases)
    create_backlog_review_ceremony_uc = CreateBacklogReviewCeremonyUseCase(
        storage=storage,
        messaging=messaging,
    )
    get_backlog_review_ceremony_uc = GetBacklogReviewCeremonyUseCase(storage=storage)
    list_backlog_review_ceremonies_uc = ListBacklogReviewCeremoniesUseCase(
        storage=storage
    )
    add_stories_to_review_uc = AddStoriesToReviewUseCase(
        storage=storage,
    )
    remove_story_from_review_uc = RemoveStoryFromReviewUseCase(
        storage=storage,
    )
    start_backlog_review_ceremony_uc = StartBacklogReviewCeremonyUseCase(
        storage=storage,
        ray_executor=ray_executor_adapter,
        messaging=messaging,
        context=context_adapter,
    )
    approve_review_plan_uc = ApproveReviewPlanUseCase(
        storage=storage,
        messaging=messaging,
    )
    reject_review_plan_uc = RejectReviewPlanUseCase(
        storage=storage,
        messaging=messaging,
    )
    complete_backlog_review_ceremony_uc = CompleteBacklogReviewCeremonyUseCase(
        storage=storage,
        messaging=messaging,
    )
    cancel_backlog_review_ceremony_uc = CancelBacklogReviewCeremonyUseCase(
        storage=storage,
        messaging=messaging,
    )

    logger.info("✓ 9 backlog review use cases initialized")

    # ProcessStoryReviewResultUseCase for AddAgentDeliberation gRPC handler
    process_story_review_result_uc = ProcessStoryReviewResultUseCase(
        storage=storage,
        messaging=messaging,
        context=context_adapter,
    )

    logger.info("✓ ProcessStoryReviewResultUseCase initialized (for AddAgentDeliberation gRPC)")

    # Create servicer with all use cases (including process_story_review_result_uc)
    servicer = PlanningServiceServicer(
        # Project use cases
        create_project_uc=create_project_uc,
        delete_project_uc=delete_project_uc,
        get_project_uc=get_project_uc,
        list_projects_uc=list_projects_uc,
        # Epic use cases
        create_epic_uc=create_epic_uc,
        delete_epic_uc=delete_epic_uc,
        get_epic_uc=get_epic_uc,
        list_epics_uc=list_epics_uc,
        # Story use cases
        create_story_uc=create_story_uc,
        delete_story_uc=delete_story_uc,
        get_story_uc=get_story_uc,
        list_stories_uc=list_stories_uc,
        transition_story_uc=transition_story_uc,
        # Task use cases
        create_task_uc=create_task_uc,
        get_task_uc=get_task_uc,
        list_tasks_uc=list_tasks_uc,
        # Decision use cases
        approve_decision_uc=approve_decision_uc,
        reject_decision_uc=reject_decision_uc,
        # Backlog Review Ceremony use cases
        create_backlog_review_ceremony_uc=create_backlog_review_ceremony_uc,
        get_backlog_review_ceremony_uc=get_backlog_review_ceremony_uc,
        list_backlog_review_ceremonies_uc=list_backlog_review_ceremonies_uc,
        add_stories_to_review_uc=add_stories_to_review_uc,
        remove_story_from_review_uc=remove_story_from_review_uc,
        start_backlog_review_ceremony_uc=start_backlog_review_ceremony_uc,
        approve_review_plan_uc=approve_review_plan_uc,
        reject_review_plan_uc=reject_review_plan_uc,
        complete_backlog_review_ceremony_uc=complete_backlog_review_ceremony_uc,
        cancel_backlog_review_ceremony_uc=cancel_backlog_review_ceremony_uc,
    )

    # Set process_story_review_result_uc in servicer for AddAgentDeliberation handler
    servicer.process_story_review_result_uc = process_story_review_result_uc

    # Thin client: Planning Ceremony Processor (optional, when PLANNING_CEREMONY_PROCESSOR_URL set)
    processor_url = config.get_planning_ceremony_processor_url()
    if processor_url:
        planning_ceremony_processor_adapter = PlanningCeremonyProcessorAdapter(
            grpc_address=processor_url
        )
        planning_ceremony_processor_uc = StartPlanningCeremonyViaProcessorUseCase(
            processor=planning_ceremony_processor_adapter
        )
        servicer.planning_ceremony_processor_uc = planning_ceremony_processor_uc
        logger.info(
            "✓ Planning Ceremony Processor thin client initialized: %s",
            processor_url,
        )

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

    # Progress tracking consumers for backlog review
    deliberations_complete_progress_consumer = DeliberationsCompleteProgressConsumer(
        nats_client=nc,
        jetstream=js,
        storage=storage,
    )

    tasks_complete_progress_consumer = TasksCompleteProgressConsumer(
        nats_client=nc,
        jetstream=js,
        storage=storage,
    )

    # Initialize dual write reconciliation service and consumer
    reconciliation_service = DualWriteReconciliationService(
        dual_write_ledger=dual_write_ledger,
        neo4j_adapter=storage.neo4j,
    )

    dual_write_reconciler_consumer = DualWriteReconcilerConsumer(
        nats_client=nc,
        jetstream=js,
        reconciliation_service=reconciliation_service,
    )

    # Start consumers in background
    await task_derivation_consumer.start()
    logger.info("✓ TaskDerivationResultConsumer started (listening to agent.response.completed)")

    await deliberations_complete_progress_consumer.start()
    logger.info(
        "✓ DeliberationsCompleteProgressConsumer started "
        "(listening to planning.backlog_review.deliberations.complete)"
    )

    await tasks_complete_progress_consumer.start()
    logger.info(
        "✓ TasksCompleteProgressConsumer started "
        "(listening to planning.backlog_review.tasks.complete)"
    )

    await dual_write_reconciler_consumer.start()
    logger.info(
        "✓ DualWriteReconcilerConsumer started "
        "(listening to planning.dualwrite.reconcile.requested)"
    )



    # Create gRPC server
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))

    planning_pb2_grpc.add_PlanningServiceServicer_to_server(servicer, server)

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

        await deliberations_complete_progress_consumer.stop()
        logger.info("✓ DeliberationsCompleteProgressConsumer stopped")

        await tasks_complete_progress_consumer.stop()
        logger.info("✓ TasksCompleteProgressConsumer stopped")

        await dual_write_reconciler_consumer.stop()
        logger.info("✓ DualWriteReconcilerConsumer stopped")



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

