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
from planning.infrastructure.adapters.environment_config_adapter import (
    EnvironmentConfigurationAdapter,
)

from planning.application.usecases import (
    ApproveDecisionUseCase,
    CreateStoryUseCase,
    InvalidTransitionError,
    ListStoriesUseCase,
    RejectDecisionUseCase,
    StoryNotFoundError,
    TransitionStoryUseCase,
)
from planning.domain import StoryId, StoryState, StoryStateEnum
from planning.infrastructure.adapters import (
    NATSMessagingAdapter,
    Neo4jConfig,
    StorageAdapter,
    ValkeyConfig,
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
        create_story_uc: CreateStoryUseCase,
        list_stories_uc: ListStoriesUseCase,
        transition_story_uc: TransitionStoryUseCase,
        approve_decision_uc: ApproveDecisionUseCase,
        reject_decision_uc: RejectDecisionUseCase,
    ):
        """Initialize servicer with use cases."""
        self.create_story_uc = create_story_uc
        self.list_stories_uc = list_stories_uc
        self.transition_story_uc = transition_story_uc
        self.approve_decision_uc = approve_decision_uc
        self.reject_decision_uc = reject_decision_uc

        logger.info("Planning Service servicer initialized")

    async def CreateStory(self, request, context):
        """Create a new user story."""
        try:
            logger.info(f"CreateStory: title={request.title}, created_by={request.created_by}")

            story = await self.create_story_uc.execute(
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

    # Initialize use cases
    create_story_uc = CreateStoryUseCase(storage=storage, messaging=messaging)
    list_stories_uc = ListStoriesUseCase(storage=storage)
    transition_story_uc = TransitionStoryUseCase(storage=storage, messaging=messaging)
    approve_decision_uc = ApproveDecisionUseCase(messaging=messaging)
    reject_decision_uc = RejectDecisionUseCase(messaging=messaging)

    # Create gRPC server
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))

    planning_pb2_grpc.add_PlanningServiceServicer_to_server(
        PlanningServiceServicer(
            create_story_uc=create_story_uc,
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

