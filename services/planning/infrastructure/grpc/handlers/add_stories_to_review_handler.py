"""AddStoriesToReview gRPC handler."""

import logging

from planning.application.usecases import AddStoriesToReviewUseCase, CeremonyNotFoundError
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.gen import planning_pb2
from planning.infrastructure.mappers.response_protobuf_mapper import (
    ResponseProtobufMapper,
)

import grpc

logger = logging.getLogger(__name__)


async def add_stories_to_review_handler(
    request: planning_pb2.AddStoriesToReviewRequest,
    context,
    use_case: AddStoriesToReviewUseCase,
) -> planning_pb2.AddStoriesToReviewResponse:
    """Handle AddStoriesToReview RPC."""
    try:
        logger.info(
            f"AddStoriesToReview: ceremony_id={request.ceremony_id}, "
            f"stories={len(request.story_ids)}"
        )

        ceremony_id = BacklogReviewCeremonyId(request.ceremony_id)
        story_ids = tuple(StoryId(sid) for sid in request.story_ids)

        ceremony = await use_case.execute(ceremony_id, story_ids)

        return ResponseProtobufMapper.add_stories_to_review_response(
            success=True,
            message=f"Added {len(story_ids)} stories to ceremony",
            ceremony=ceremony,
        )

    except CeremonyNotFoundError as e:
        logger.warning(f"Ceremony not found: {e}")
        context.set_code(grpc.StatusCode.NOT_FOUND)
        return ResponseProtobufMapper.add_stories_to_review_response(
            success=False,
            message=str(e),
        )

    except ValueError as e:
        error_message = str(e)
        logger.warning(f"AddStoriesToReview validation error: {error_message}")
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        return ResponseProtobufMapper.add_stories_to_review_response(
            success=False,
            message=error_message,
        )

    except Exception as e:
        error_message = f"Internal error: {e}"
        logger.error(f"AddStoriesToReview error: {error_message}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return ResponseProtobufMapper.add_stories_to_review_response(
            success=False,
            message=error_message,
        )






