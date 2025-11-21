"""CreateStory gRPC handler."""

import logging

from planning.application.usecases.create_story_usecase import CreateStoryUseCase
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.gen import planning_pb2
from planning.infrastructure.grpc.mappers.response_mapper import ResponseMapper

import grpc

logger = logging.getLogger(__name__)


async def create_story_handler(
    request: planning_pb2.CreateStoryRequest,
    context,
    use_case: CreateStoryUseCase,
) -> planning_pb2.CreateStoryResponse:
    """Handle CreateStory RPC."""
    try:
        logger.info(f"CreateStory: epic_id={request.epic_id}, title={request.title}")

        epic_id = EpicId(request.epic_id)
        story = await use_case.execute(
            epic_id=epic_id,
            title=request.title,
            brief=request.brief,
            created_by=request.created_by,
        )

        return ResponseMapper.create_story_response(
            success=True,
            message=f"Story created: {story.story_id.value}",
            story=story,
        )

    except ValueError as e:
        logger.warning(f"CreateStory validation error: {e}")
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        return ResponseMapper.create_story_response(success=False, message=str(e))

    except Exception as e:
        logger.error(f"CreateStory error: {e}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return ResponseMapper.create_story_response(success=False, message=f"Internal error: {e}")


async def create_story(
    request: planning_pb2.CreateStoryRequest,
    context,
    use_case: CreateStoryUseCase,
) -> planning_pb2.CreateStoryResponse:
    """Backward-compatibility shim."""
    return await create_story_handler(request, context, use_case)

