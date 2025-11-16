"""ListStories gRPC handler."""

import logging

from planning.gen import planning_pb2

import grpc
from planning.application.usecases.list_stories_usecase import ListStoriesUseCase
from planning.domain.value_objects.statuses.story_state import StoryState, StoryStateEnum
from planning.infrastructure.grpc.mappers.response_mapper import ResponseMapper

logger = logging.getLogger(__name__)


async def list_stories_handler(
    request: planning_pb2.ListStoriesRequest,
    context,
    use_case: ListStoriesUseCase,
) -> planning_pb2.ListStoriesResponse:
    """Handle ListStories RPC."""
    try:
        state_filter = (
            StoryState(StoryStateEnum(request.state_filter))
            if request.state_filter
            else None
        )
        limit = request.limit if request.limit > 0 else 100
        offset = request.offset if request.offset >= 0 else 0

        logger.info(f"ListStories: state={state_filter}, limit={limit}")

        stories = await use_case.execute(
            state_filter=state_filter,
            limit=limit,
            offset=offset,
        )

        return ResponseMapper.list_stories_response(
            success=True,
            message=f"Found {len(stories)} stories",
            stories=stories,
            total_count=len(stories),
        )

    except Exception as e:
        logger.error(f"ListStories error: {e}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return ResponseMapper.list_stories_response(
            success=False,
            message=f"Error: {e}",
            stories=[],
            total_count=0,
        )

