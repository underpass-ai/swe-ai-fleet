"""GetStory gRPC handler."""

import logging

from planning.application.usecases.get_story_usecase import GetStoryUseCase
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.gen import planning_pb2
from planning.infrastructure.mappers.story_protobuf_mapper import StoryProtobufMapper

import grpc

logger = logging.getLogger(__name__)


async def get_story_handler(
    request: planning_pb2.GetStoryRequest,
    context,
    use_case: GetStoryUseCase,
) -> planning_pb2.Story:
    """Handle GetStory RPC.

    This handler returns Story directly (not a response wrapper).
    """
    try:
        logger.info(f"GetStory: story_id={request.story_id}")

        story_id = StoryId(request.story_id)
        story = await use_case.execute(story_id)

        if not story:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            return planning_pb2.Story()

        return StoryProtobufMapper.to_protobuf(story)

    except Exception as e:
        logger.error(f"GetStory error: {e}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return planning_pb2.Story()

