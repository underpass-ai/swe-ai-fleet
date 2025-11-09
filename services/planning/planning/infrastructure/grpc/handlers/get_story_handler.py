"""GetStory gRPC handler."""

import logging

import grpc

from planning.application.ports.storage_port import StoragePort
from planning.domain.value_objects.story_id import StoryId
from planning.gen import planning_pb2
from planning.infrastructure.mappers.story_protobuf_mapper import StoryProtobufMapper

logger = logging.getLogger(__name__)


async def get_story(
    request: planning_pb2.GetStoryRequest,
    context,
    storage: StoragePort,
) -> planning_pb2.Story:
    """Handle GetStory RPC.

    Note: This uses storage directly as there's no dedicated use case yet.
    Consider creating GetStoryUseCase for consistency.
    """
    try:
        logger.info(f"GetStory: story_id={request.story_id}")

        story_id = StoryId(request.story_id)
        story = await storage.get_story(story_id)

        if not story:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            return planning_pb2.Story()

        return StoryProtobufMapper.to_protobuf(story)

    except Exception as e:
        logger.error(f"GetStory error: {e}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return planning_pb2.Story()

