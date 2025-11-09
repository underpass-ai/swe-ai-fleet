"""TransitionStory gRPC handler."""

import logging

import grpc

from planning.application.usecases.transition_story_usecase import TransitionStoryUseCase
from planning.domain.value_objects.story_id import StoryId
from planning.domain.value_objects.story_state import StoryState
from planning.gen import planning_pb2
from planning.infrastructure.mappers.story_protobuf_mapper import StoryProtobufMapper

logger = logging.getLogger(__name__)


async def transition_story(
    request: planning_pb2.TransitionStoryRequest,
    context,
    use_case: TransitionStoryUseCase,
) -> planning_pb2.TransitionStoryResponse:
    """Handle TransitionStory RPC."""
    try:
        logger.info(f"TransitionStory: story_id={request.story_id}, to={request.to_state}")

        story_id = StoryId(request.story_id)
        to_state = StoryState(request.to_state)

        story = await use_case.execute(
            story_id=story_id,
            to_state=to_state,
            transitioned_by=request.transitioned_by,
        )

        return planning_pb2.TransitionStoryResponse(
            success=True,
            message=f"Story transitioned to {to_state.value}",
            story=StoryProtobufMapper.to_protobuf(story),
        )

    except ValueError as e:
        logger.warning(f"TransitionStory validation error: {e}")
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        return planning_pb2.TransitionStoryResponse(success=False, message=str(e))

    except Exception as e:
        logger.error(f"TransitionStory error: {e}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return planning_pb2.TransitionStoryResponse(success=False, message=f"Internal error: {e}")

