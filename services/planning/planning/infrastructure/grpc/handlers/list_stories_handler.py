"""ListStories gRPC handler."""

import logging

import grpc

from planning.application.usecases.list_stories_usecase import ListStoriesUseCase
from planning.domain.value_objects.story_state import StoryState
from planning.gen import planning_pb2
from planning.infrastructure.mappers.story_protobuf_mapper import StoryProtobufMapper

logger = logging.getLogger(__name__)


async def list_stories(
    request: planning_pb2.ListStoriesRequest,
    context,
    use_case: ListStoriesUseCase,
) -> planning_pb2.ListStoriesResponse:
    """Handle ListStories RPC."""
    try:
        state_filter = StoryState(request.state_filter) if request.state_filter else None
        limit = request.limit if request.limit > 0 else 100
        offset = request.offset if request.offset >= 0 else 0

        logger.info(f"ListStories: state={state_filter}, limit={limit}")

        stories = await use_case.execute(
            state_filter=state_filter,
            limit=limit,
            offset=offset,
        )

        return planning_pb2.ListStoriesResponse(
            success=True,
            message=f"Found {len(stories)} stories",
            stories=[StoryProtobufMapper.to_protobuf(s) for s in stories],
            total_count=len(stories),
        )

    except Exception as e:
        logger.error(f"ListStories error: {e}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return planning_pb2.ListStoriesResponse(
            success=False,
            message=f"Error: {e}",
            stories=[],
            total_count=0,
        )

