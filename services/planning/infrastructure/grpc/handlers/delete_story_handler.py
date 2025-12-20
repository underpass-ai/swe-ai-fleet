"""DeleteStory gRPC handler."""

import logging

from planning.application.usecases.delete_story_usecase import DeleteStoryUseCase
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.gen import planning_pb2

import grpc

logger = logging.getLogger(__name__)


async def delete_story_handler(
    request: planning_pb2.DeleteStoryRequest,
    context,
    use_case: DeleteStoryUseCase,
) -> planning_pb2.DeleteStoryResponse:
    """Handle DeleteStory RPC."""
    try:
        logger.info(f"DeleteStory: story_id={request.story_id}")

        if not request.story_id:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            return planning_pb2.DeleteStoryResponse(
                success=False,
                message="story_id is required",
            )

        story_id = StoryId(request.story_id)
        await use_case.execute(story_id)

        return planning_pb2.DeleteStoryResponse(
            success=True,
            message=f"Story deleted: {story_id.value}",
        )

    except ValueError as e:
        logger.warning(f"DeleteStory validation error: {e}")
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        return planning_pb2.DeleteStoryResponse(success=False, message=str(e))

    except Exception as e:
        logger.error(f"DeleteStory error: {e}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return planning_pb2.DeleteStoryResponse(
            success=False,
            message=f"Internal error: {e}",
        )
