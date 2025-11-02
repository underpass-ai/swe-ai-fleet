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

from planning.application.usecases import (
    CreateStoryUseCase,
    ListStoriesUseCase,
    TransitionStoryUseCase,
    ApproveDecisionUseCase,
    RejectDecisionUseCase,
    StoryNotFoundError,
    InvalidTransitionError,
)
from planning.domain import StoryId, StoryState, StoryStateEnum
from planning.infrastructure.adapters import (
    StorageAdapter,
    Neo4jConfig,
    ValkeyConfig,
    NATSMessagingAdapter,
)
from planning.gen import planning_pb2, planning_pb2_grpc

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
            
            return planning_pb2.CreateStoryResponse(
                story=self._story_to_pb(story),
                success=True,
                message=f"Story created: {story.story_id.value}",
            )
        
        except ValueError as e:
            logger.warning(f"CreateStory validation error: {e}")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return planning_pb2.CreateStoryResponse(
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
            
            return planning_pb2.ListStoriesResponse(
                stories=[self._story_to_pb(story) for story in stories],
                total_count=len(stories),
                success=True,
                message=f"Found {len(stories)} stories",
            )
        
        except Exception as e:
            logger.error(f"ListStories error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return planning_pb2.ListStoriesResponse(
                success=False,
                message=f"Error: {e}",
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
            
            return planning_pb2.TransitionStoryResponse(
                story=self._story_to_pb(story),
                success=True,
                message=f"Story transitioned to {target_state}",
            )
        
        except StoryNotFoundError as e:
            logger.warning(f"TransitionStory: story not found: {e}")
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(str(e))
            return planning_pb2.TransitionStoryResponse(
                success=False,
                message=str(e),
            )
        
        except InvalidTransitionError as e:
            logger.warning(f"TransitionStory: invalid transition: {e}")
            context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
            context.set_details(str(e))
            return planning_pb2.TransitionStoryResponse(
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
            
            return planning_pb2.ApproveDecisionResponse(
                success=True,
                message=f"Decision {request.decision_id} approved",
            )
        
        except ValueError as e:
            logger.warning(f"ApproveDecision validation error: {e}")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return planning_pb2.ApproveDecisionResponse(
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
            
            return planning_pb2.RejectDecisionResponse(
                success=True,
                message=f"Decision {request.decision_id} rejected",
            )
        
        except ValueError as e:
            logger.warning(f"RejectDecision validation error: {e}")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return planning_pb2.RejectDecisionResponse(
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
            
            return self._story_to_pb(story)
        
        except Exception as e:
            logger.error(f"GetStory error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return planning_pb2.Story()
    
    def _story_to_pb(self, story) -> planning_pb2.Story:
        """Convert domain Story to protobuf Story."""
        return planning_pb2.Story(
            story_id=story.story_id.value,
            title=story.title,
            brief=story.brief,
            state=story.state.value.value,
            dor_score=story.dor_score.value,
            created_by=story.created_by,
            created_at=story.created_at.isoformat() + "Z",
            updated_at=story.updated_at.isoformat() + "Z",
        )


async def main():
    """Initialize and run Planning Service."""
    # Load configuration from environment
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    neo4j_database = os.getenv("NEO4J_DATABASE")
    
    valkey_host = os.getenv("VALKEY_HOST", "valkey")
    valkey_port = int(os.getenv("VALKEY_PORT", "6379"))
    valkey_url = f"redis://{valkey_host}:{valkey_port}/0"
    
    nats_url = os.getenv("NATS_URL", "nats://nats:4222")
    
    grpc_port = int(os.getenv("GRPC_PORT", "50054"))
    
    logger.info(f"Starting Planning Service on port {grpc_port}")
    logger.info(f"Neo4j: {neo4j_uri}, Valkey: {valkey_url}, NATS: {nats_url}")
    
    # Initialize NATS connection
    nc = NATS()
    await nc.connect(nats_url)
    js = nc.jetstream()
    logger.info("Connected to NATS JetStream")
    
    # Initialize adapters
    neo4j_config = Neo4jConfig(
        uri=neo4j_uri,
        user=neo4j_user,
        password=neo4j_password,
        database=neo4j_database,
    )
    
    valkey_config = ValkeyConfig(
        host=valkey_host,
        port=valkey_port,
        db=0,
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

