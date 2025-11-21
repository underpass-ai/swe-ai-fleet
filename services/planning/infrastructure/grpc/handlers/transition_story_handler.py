"""TransitionStory gRPC handler."""

import logging

from planning.gen import planning_pb2

import grpc
from planning.application.usecases import InvalidTransitionError, StoryNotFoundError
from planning.application.usecases.transition_story_usecase import (
    TasksNotReadyError,
    TransitionStoryUseCase,
)
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.statuses.story_state import StoryState, StoryStateEnum
from planning.infrastructure.grpc.mappers.response_mapper import ResponseMapper

logger = logging.getLogger(__name__)


async def transition_story_handler(
    request: planning_pb2.TransitionStoryRequest,
    context,
    use_case: TransitionStoryUseCase,
) -> planning_pb2.TransitionStoryResponse:
    """Handle TransitionStory RPC."""
    try:
        logger.info(f"TransitionStory: story_id={request.story_id}, to={request.target_state}")

        story_id = StoryId(request.story_id)
        to_state = StoryState(StoryStateEnum(request.target_state))

        story = await use_case.execute(
            story_id=story_id,
            to_state=to_state,
            transitioned_by=request.transitioned_by,
        )

        return ResponseMapper.transition_story_response(
            success=True,
            message=f"Story transitioned to {to_state.value}",
            story=story,
        )

    except StoryNotFoundError as e:
        logger.warning(f"TransitionStory: story not found: {e}")
        context.set_code(grpc.StatusCode.NOT_FOUND)
        return ResponseMapper.transition_story_response(success=False, message=str(e))

    except InvalidTransitionError as e:
        logger.warning(f"TransitionStory: invalid transition: {e}")
        context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
        return ResponseMapper.transition_story_response(success=False, message=str(e))

    except TasksNotReadyError as e:
        logger.warning(f"TransitionStory: tasks not ready: {e}")
        context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
        return ResponseMapper.transition_story_response(success=False, message=str(e))

    except ValueError as e:
        logger.warning(f"TransitionStory validation error: {e}")
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        return ResponseMapper.transition_story_response(success=False, message=str(e))

    except Exception as e:
        logger.error(f"TransitionStory error: {e}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return ResponseMapper.transition_story_response(success=False, message=f"Internal error: {e}")

