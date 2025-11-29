"""CreateStory gRPC handler."""

import logging

from planning.application.usecases.create_story_usecase import CreateStoryUseCase
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.content.brief import Brief
from planning.domain.value_objects.content.title import Title
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

        # Convert protobuf primitives → Value Objects (Fail Fast)
        epic_id = EpicId(request.epic_id)
        title = Title(request.title)
        brief = Brief(request.brief)
        created_by = UserName(request.created_by)

        story = await use_case.execute(
            epic_id=epic_id,
            title=title,
            brief=brief,
            created_by=created_by,
        )

        return ResponseMapper.create_story_response(
            success=True,
            message=f"Story created: {story.story_id.value}",
            story=story,
        )

    except ValueError as e:
        error_message = str(e) if e else "Validation error"
        logger.warning(f"CreateStory validation error: {error_message}")
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        context.set_details(error_message)
        return ResponseMapper.create_story_response(success=False, message=error_message)

    except Exception as e:
        error_message = f"Internal error: {e}" if e else "Internal error"
        logger.error(f"CreateStory error: {error_message}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        context.set_details(error_message)
        return ResponseMapper.create_story_response(success=False, message=error_message)


async def create_story(
    request: planning_pb2.CreateStoryRequest,
    context,
    use_case: CreateStoryUseCase,
) -> planning_pb2.CreateStoryResponse:
    """Backward-compatibility shim."""
    return await create_story_handler(request, context, use_case)

