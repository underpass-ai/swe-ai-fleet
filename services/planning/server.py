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
from planning.domain import StoryId, StoryState, StoryStateEnum
from planning.domain.value_objects.epic_id import EpicId
from planning.domain.value_objects.plan_id import PlanId
from planning.domain.value_objects.project_id import ProjectId
from planning.domain.value_objects.task_id import TaskId
from planning.domain.value_objects.task_type import TaskType
from planning.infrastructure.adapters import (
    NATSMessagingAdapter,
    Neo4jConfig,
    StorageAdapter,
    ValkeyConfig,
)
from planning.infrastructure.adapters.environment_config_adapter import (
    EnvironmentConfigurationAdapter,
)
from planning.infrastructure.mappers import (
    ResponseProtobufMapper,
    StoryProtobufMapper,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class PlanningServiceServicer(planning_pb2_grpc.PlanningServiceServicer):
    """gRPC servicer for Planning Service."""

    def __init__(
        self,
        create_project_uc: CreateProjectUseCase,
        create_epic_uc: CreateEpicUseCase,
        create_story_uc: CreateStoryUseCase,
        create_task_uc: CreateTaskUseCase,
        list_stories_uc: ListStoriesUseCase,
        transition_story_uc: TransitionStoryUseCase,
        approve_decision_uc: ApproveDecisionUseCase,
        reject_decision_uc: RejectDecisionUseCase,
    ):
        """Initialize servicer with use cases."""
        self.create_project_uc = create_project_uc
        self.create_epic_uc = create_epic_uc
        self.create_story_uc = create_story_uc
        self.create_task_uc = create_task_uc
        self.list_stories_uc = list_stories_uc
        self.transition_story_uc = transition_story_uc
        self.approve_decision_uc = approve_decision_uc
        self.reject_decision_uc = reject_decision_uc

        logger.info("Planning Service servicer initialized with hierarchy support")

    # ========== Project Management (Root of Hierarchy) ==========

    async def CreateProject(self, request, context):
        """Create a new project (root of hierarchy)."""
        try:
            logger.info(f"CreateProject: name={request.name}, owner={request.owner}")

            project = await self.create_project_uc.execute(
                name=request.name,
                description=request.description,
                owner=request.owner,
            )

            return planning_pb2.CreateProjectResponse(
                success=True,
                message=f"Project created: {project.project_id.value}",
                project=planning_pb2.Project(
                    project_id=project.project_id.value,
                    name=project.name,
                    description=project.description,
                    status=project.status.value,
                    owner=project.owner,
                    created_at=project.created_at.isoformat() + "Z",
                    updated_at=project.updated_at.isoformat() + "Z",
                ),
            )

        except ValueError as e:
            logger.warning(f"CreateProject validation error: {e}")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return planning_pb2.CreateProjectResponse(
                success=False,
                message=str(e),
            )

        except Exception as e:
            logger.error(f"CreateProject error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {e}")
            return planning_pb2.CreateProjectResponse(
                success=False,
                message=f"Internal error: {e}",
            )

    async def GetProject(self, request, context):
        """Get a single project by ID."""
        try:
            logger.info(f"GetProject: project_id={request.project_id}")

            project_id = ProjectId(request.project_id)
            project = await self.list_stories_uc.storage.get_project(project_id)

            if project is None:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Project not found: {request.project_id}")
                return planning_pb2.ProjectResponse()

            return planning_pb2.ProjectResponse(
                project=planning_pb2.Project(
                    project_id=project.project_id.value,
                    name=project.name,
                    description=project.description,
                    status=project.status.value,
                    owner=project.owner,
                    created_at=project.created_at.isoformat() + "Z",
                    updated_at=project.updated_at.isoformat() + "Z",
                ),
            )

        except Exception as e:
            logger.error(f"GetProject error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return planning_pb2.ProjectResponse()

    async def ListProjects(self, request, context):
        """List all projects."""
        try:
            logger.info(f"ListProjects: limit={request.limit}, offset={request.offset}")

            limit = request.limit if request.limit > 0 else 100
            offset = request.offset if request.offset >= 0 else 0

            projects = await self.list_stories_uc.storage.list_projects(limit=limit, offset=offset)

            return planning_pb2.ListProjectsResponse(
                success=True,
                message=f"Found {len(projects)} projects",
                projects=[
                    planning_pb2.Project(
                        project_id=p.project_id.value,
                        name=p.name,
                        description=p.description,
                        status=p.status.value,
                        owner=p.owner,
                        created_at=p.created_at.isoformat() + "Z",
                        updated_at=p.updated_at.isoformat() + "Z",
                    )
                    for p in projects
                ],
                total_count=len(projects),
            )

        except Exception as e:
            logger.error(f"ListProjects error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return planning_pb2.ListProjectsResponse(
                success=False,
                message=f"Error: {e}",
                projects=[],
                total_count=0,
            )

    # ========== Epic Management (Groups Stories) ==========

    async def CreateEpic(self, request, context):
        """Create a new epic under a project."""
        try:
            logger.info(f"CreateEpic: project_id={request.project_id}, title={request.title}")

            project_id = ProjectId(request.project_id)

            epic = await self.create_epic_uc.execute(
                project_id=project_id,
                title=request.title,
                description=request.description,
            )

            return planning_pb2.CreateEpicResponse(
                success=True,
                message=f"Epic created: {epic.epic_id.value}",
                epic=planning_pb2.Epic(
                    epic_id=epic.epic_id.value,
                    project_id=epic.project_id.value,
                    title=epic.title,
                    description=epic.description,
                    status=epic.status.value,
                    created_at=epic.created_at.isoformat() + "Z",
                    updated_at=epic.updated_at.isoformat() + "Z",
                ),
            )

        except ValueError as e:
            logger.warning(f"CreateEpic validation error: {e}")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return planning_pb2.CreateEpicResponse(
                success=False,
                message=str(e),
            )

        except Exception as e:
            logger.error(f"CreateEpic error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {e}")
            return planning_pb2.CreateEpicResponse(
                success=False,
                message=f"Internal error: {e}",
            )

    async def GetEpic(self, request, context):
        """Get a single epic by ID."""
        try:
            logger.info(f"GetEpic: epic_id={request.epic_id}")

            epic_id = EpicId(request.epic_id)
            epic = await self.list_stories_uc.storage.get_epic(epic_id)

            if epic is None:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Epic not found: {request.epic_id}")
                return planning_pb2.EpicResponse()

            return planning_pb2.EpicResponse(
                epic=planning_pb2.Epic(
                    epic_id=epic.epic_id.value,
                    project_id=epic.project_id.value,
                    title=epic.title,
                    description=epic.description,
                    status=epic.status.value,
                    created_at=epic.created_at.isoformat() + "Z",
                    updated_at=epic.updated_at.isoformat() + "Z",
                ),
            )

        except Exception as e:
            logger.error(f"GetEpic error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return planning_pb2.EpicResponse()

    async def ListEpics(self, request, context):
        """List epics for a project."""
        try:
            project_id = ProjectId(request.project_id) if request.project_id else None
            limit = request.limit if request.limit > 0 else 100
            offset = request.offset if request.offset >= 0 else 0

            logger.info(f"ListEpics: project_id={project_id}, limit={limit}")

            epics = await self.list_stories_uc.storage.list_epics(
                project_id=project_id,
                limit=limit,
                offset=offset,
            )

            return planning_pb2.ListEpicsResponse(
                success=True,
                message=f"Found {len(epics)} epics",
                epics=[
                    planning_pb2.Epic(
                        epic_id=e.epic_id.value,
                        project_id=e.project_id.value,
                        title=e.title,
                        description=e.description,
                        status=e.status.value,
                        created_at=e.created_at.isoformat() + "Z",
                        updated_at=e.updated_at.isoformat() + "Z",
                    )
                    for e in epics
                ],
                total_count=len(epics),
            )

        except Exception as e:
            logger.error(f"ListEpics error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return planning_pb2.ListEpicsResponse(
                success=False,
                message=f"Error: {e}",
                epics=[],
                total_count=0,
            )

    # ========== Story Management (User Stories) ==========

    async def CreateStory(self, request, context):
        """Create a new user story."""
        try:
            logger.info(f"CreateStory: epic_id={request.epic_id}, title={request.title}")

            epic_id = EpicId(request.epic_id)

            story = await self.create_story_uc.execute(
                epic_id=epic_id,  # REQUIRED - domain invariant
                title=request.title,
                brief=request.brief,
                created_by=request.created_by,
            )

            return ResponseProtobufMapper.create_story_response(
                success=True,
                message=f"Story created: {story.story_id.value}",
                story=story,
            )

        except ValueError as e:
            logger.warning(f"CreateStory validation error: {e}")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return ResponseProtobufMapper.create_story_response(
                success=False,
                message=str(e),
            )

        except Exception as e:
            logger.error(f"CreateStory error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {e}")
            return planning_pb2.CreateStoryResponse(
                success=False,
                message=f"Internal error: {e}",
            )

    async def ListStories(self, request, context):
        """List stories with optional filtering."""
        try:
            state_filter = None
            if request.HasField("state_filter"):
                state_filter = StoryState(StoryStateEnum(request.state_filter))

            limit = request.limit if request.limit > 0 else 100
            offset = request.offset if request.offset >= 0 else 0

            logger.info(f"ListStories: state={state_filter}, limit={limit}, offset={offset}")

            stories = await self.list_stories_uc.execute(
                state_filter=state_filter,
                limit=limit,
                offset=offset,
            )

            return ResponseProtobufMapper.list_stories_response(
                success=True,
                message=f"Found {len(stories)} stories",
                stories=stories,
                total_count=len(stories),
            )

        except Exception as e:
            logger.error(f"ListStories error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return ResponseProtobufMapper.list_stories_response(
                success=False,
                message=f"Error: {e}",
                stories=[],
                total_count=0,
            )

    async def TransitionStory(self, request, context):
        """Transition story to a new state."""
        try:
            logger.info(
                f"TransitionStory: story_id={request.story_id}, "
                f"target={request.target_state}, by={request.transitioned_by}"
            )

            story_id = StoryId(request.story_id)
            target_state = StoryState(StoryStateEnum(request.target_state))

            story = await self.transition_story_uc.execute(
                story_id=story_id,
                target_state=target_state,
                transitioned_by=request.transitioned_by,
            )

            return ResponseProtobufMapper.transition_story_response(
                success=True,
                message=f"Story transitioned to {target_state}",
                story=story,
            )

        except StoryNotFoundError as e:
            logger.warning(f"TransitionStory: story not found: {e}")
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(str(e))
            return ResponseProtobufMapper.transition_story_response(
                success=False,
                message=str(e),
            )

        except InvalidTransitionError as e:
            logger.warning(f"TransitionStory: invalid transition: {e}")
            context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
            context.set_details(str(e))
            return ResponseProtobufMapper.transition_story_response(
                success=False,
                message=str(e),
            )

        except Exception as e:
            logger.error(f"TransitionStory error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return planning_pb2.TransitionStoryResponse(
                success=False,
                message=f"Internal error: {e}",
            )

    async def ApproveDecision(self, request, context):
        """Approve a decision for a story."""
        try:
            logger.info(
                f"ApproveDecision: story_id={request.story_id}, "
                f"decision_id={request.decision_id}, by={request.approved_by}"
            )

            story_id = StoryId(request.story_id)
            comment = request.comment if request.HasField("comment") else None

            await self.approve_decision_uc.execute(
                story_id=story_id,
                decision_id=request.decision_id,
                approved_by=request.approved_by,
                comment=comment,
            )

            return ResponseProtobufMapper.approve_decision_response(
                success=True,
                message=f"Decision {request.decision_id} approved",
            )

        except ValueError as e:
            logger.warning(f"ApproveDecision validation error: {e}")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return ResponseProtobufMapper.approve_decision_response(
                success=False,
                message=str(e),
            )

        except Exception as e:
            logger.error(f"ApproveDecision error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return planning_pb2.ApproveDecisionResponse(
                success=False,
                message=f"Internal error: {e}",
            )

    async def RejectDecision(self, request, context):
        """Reject a decision for a story."""
        try:
            logger.info(
                f"RejectDecision: story_id={request.story_id}, "
                f"decision_id={request.decision_id}, by={request.rejected_by}"
            )

            story_id = StoryId(request.story_id)

            await self.reject_decision_uc.execute(
                story_id=story_id,
                decision_id=request.decision_id,
                rejected_by=request.rejected_by,
                reason=request.reason,
            )

            return ResponseProtobufMapper.reject_decision_response(
                success=True,
                message=f"Decision {request.decision_id} rejected",
            )

        except ValueError as e:
            logger.warning(f"RejectDecision validation error: {e}")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return ResponseProtobufMapper.reject_decision_response(
                success=False,
                message=str(e),
            )

        except Exception as e:
            logger.error(f"RejectDecision error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return planning_pb2.RejectDecisionResponse(
                success=False,
                message=f"Internal error: {e}",
            )

    async def GetStory(self, request, context):
        """Get a single story by ID."""
        try:
            logger.info(f"GetStory: story_id={request.story_id}")

            story_id = StoryId(request.story_id)
            # Reuse list use case with filtering (could create dedicated GetStory UC)
            storage = self.list_stories_uc.storage
            story = await storage.get_story(story_id)

            if story is None:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Story not found: {request.story_id}")
                return planning_pb2.Story()

            return StoryProtobufMapper.to_protobuf(story)

        except Exception as e:
            logger.error(f"GetStory error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return planning_pb2.Story()

    # ========== Task Management (Atomic Work Items) ==========

    async def CreateTask(self, request, context):
        """Create a new task within a plan."""
        try:
            logger.info(
                f"CreateTask: plan_id={request.plan_id}, story_id={request.story_id}, "
                f"title={request.title}"
            )

            plan_id = PlanId(request.plan_id)
            story_id = StoryId(request.story_id)
            task_type = TaskType(request.type) if request.type else TaskType.DEVELOPMENT

            task = await self.create_task_uc.execute(
                plan_id=plan_id,
                story_id=story_id,
                title=request.title,
                description=request.description,
                type=task_type,
                assigned_to=request.assigned_to,
                estimated_hours=request.estimated_hours,
                priority=request.priority if request.priority > 0 else 1,
            )

            return planning_pb2.CreateTaskResponse(
                success=True,
                message=f"Task created: {task.task_id.value}",
                task=planning_pb2.Task(
                    task_id=task.task_id.value,
                    plan_id=task.plan_id.value,
                    story_id=task.story_id.value,
                    title=task.title,
                    description=task.description,
                    type=task.type.value,
                    status=task.status.value,
                    assigned_to=task.assigned_to,
                    estimated_hours=task.estimated_hours,
                    priority=task.priority,
                    created_at=task.created_at.isoformat() + "Z",
                    updated_at=task.updated_at.isoformat() + "Z",
                ),
            )

        except ValueError as e:
            logger.warning(f"CreateTask validation error: {e}")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return planning_pb2.CreateTaskResponse(
                success=False,
                message=str(e),
            )

        except Exception as e:
            logger.error(f"CreateTask error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {e}")
            return planning_pb2.CreateTaskResponse(
                success=False,
                message=f"Internal error: {e}",
            )

    async def GetTask(self, request, context):
        """Get a single task by ID."""
        try:
            logger.info(f"GetTask: task_id={request.task_id}")

            task_id = TaskId(request.task_id)
            task = await self.list_stories_uc.storage.get_task(task_id)

            if task is None:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Task not found: {request.task_id}")
                return planning_pb2.TaskResponse()

            return planning_pb2.TaskResponse(
                task=planning_pb2.Task(
                    task_id=task.task_id.value,
                    plan_id=task.plan_id.value,
                    story_id=task.story_id.value,
                    title=task.title,
                    description=task.description,
                    type=task.type.value,
                    status=task.status.value,
                    assigned_to=task.assigned_to,
                    estimated_hours=task.estimated_hours,
                    priority=task.priority,
                    created_at=task.created_at.isoformat() + "Z",
                    updated_at=task.updated_at.isoformat() + "Z",
                ),
            )

        except Exception as e:
            logger.error(f"GetTask error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return planning_pb2.TaskResponse()

    async def ListTasks(self, request, context):
        """List tasks for a story or plan."""
        try:
            story_id = StoryId(request.story_id) if request.story_id else None
            plan_id = PlanId(request.plan_id) if request.plan_id else None
            limit = request.limit if request.limit > 0 else 100
            offset = request.offset if request.offset >= 0 else 0

            logger.info(f"ListTasks: story_id={story_id}, plan_id={plan_id}, limit={limit}")

            tasks = await self.list_stories_uc.storage.list_tasks(
                story_id=story_id,
                plan_id=plan_id,
                limit=limit,
                offset=offset,
            )

            return planning_pb2.ListTasksResponse(
                success=True,
                message=f"Found {len(tasks)} tasks",
                tasks=[
                    planning_pb2.Task(
                        task_id=t.task_id.value,
                        plan_id=t.plan_id.value,
                        story_id=t.story_id.value,
                        title=t.title,
                        description=t.description,
                        type=t.type.value,
                        status=t.status.value,
                        assigned_to=t.assigned_to,
                        estimated_hours=t.estimated_hours,
                        priority=t.priority,
                        created_at=t.created_at.isoformat() + "Z",
                        updated_at=t.updated_at.isoformat() + "Z",
                    )
                    for t in tasks
                ],
                total_count=len(tasks),
            )

        except Exception as e:
            logger.error(f"ListTasks error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return planning_pb2.ListTasksResponse(
                success=False,
                message=f"Error: {e}",
                tasks=[],
                total_count=0,
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

    storage = StorageAdapter(
        neo4j_config=neo4j_config,
        valkey_config=valkey_config,
    )

    messaging = NATSMessagingAdapter(nats_client=nc, jetstream=js)

    # Initialize use cases (hierarchy support)
    create_project_uc = CreateProjectUseCase(storage=storage, messaging=messaging)
    create_epic_uc = CreateEpicUseCase(storage=storage, messaging=messaging)
    create_story_uc = CreateStoryUseCase(storage=storage, messaging=messaging)
    create_task_uc = CreateTaskUseCase(storage=storage, messaging=messaging)
    list_stories_uc = ListStoriesUseCase(storage=storage)
    transition_story_uc = TransitionStoryUseCase(storage=storage, messaging=messaging)
    approve_decision_uc = ApproveDecisionUseCase(messaging=messaging)
    reject_decision_uc = RejectDecisionUseCase(messaging=messaging)

    logger.info("Use cases initialized with complete hierarchy support")

    # Create gRPC server
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))

    planning_pb2_grpc.add_PlanningServiceServicer_to_server(
        PlanningServiceServicer(
            create_project_uc=create_project_uc,
            create_epic_uc=create_epic_uc,
            create_story_uc=create_story_uc,
            create_task_uc=create_task_uc,
            list_stories_uc=list_stories_uc,
            transition_story_uc=transition_story_uc,
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
        await server.stop(grace=5)
        await nc.close()
        storage.close()
        logger.info("✓ Planning Service stopped")


if __name__ == "__main__":
    asyncio.run(main())

