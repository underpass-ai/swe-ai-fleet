"""RemoveStoryFromReview gRPC handler."""

import logging

from planning.application.usecases import CeremonyNotFoundError, RemoveStoryFromReviewUseCase
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.gen import planning_pb2
from planning.infrastructure.mappers.backlog_review_ceremony_protobuf_mapper import (
    BacklogReviewCeremonyProtobufMapper,
)

import grpc

logger = logging.getLogger(__name__)


async def remove_story_from_review_handler(
    request: planning_pb2.RemoveStoryFromReviewRequest,
    context,
    use_case: RemoveStoryFromReviewUseCase,
) -> planning_pb2.RemoveStoryFromReviewResponse:
    """Handle RemoveStoryFromReview RPC."""
    try:
        logger.info(
            f"RemoveStoryFromReview: ceremony_id={request.ceremony_id}, "
            f"story_id={request.story_id}"
        )

        ceremony_id = BacklogReviewCeremonyId(request.ceremony_id)
        story_id = StoryId(request.story_id)

        ceremony = await use_case.execute(ceremony_id, story_id)

        ceremony_pb = BacklogReviewCeremonyProtobufMapper.to_protobuf(ceremony)

        return planning_pb2.RemoveStoryFromReviewResponse(
            success=True,
            message=f"Removed story {story_id.value} from ceremony",
            ceremony=ceremony_pb,
        )

    except CeremonyNotFoundError as e:
        logger.warning(f"Ceremony not found: {e}")
        context.set_code(grpc.StatusCode.NOT_FOUND)
        return planning_pb2.RemoveStoryFromReviewResponse(
            success=False,
            message=str(e),
        )

    except ValueError as e:
        error_message = str(e)
        logger.warning(f"RemoveStoryFromReview validation error: {error_message}")
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        return planning_pb2.RemoveStoryFromReviewResponse(
            success=False,
            message=error_message,
        )

    except Exception as e:
        error_message = f"Internal error: {e}"
        logger.error(f"RemoveStoryFromReview error: {error_message}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return planning_pb2.RemoveStoryFromReviewResponse(
            success=False,
            message=error_message,
        )

