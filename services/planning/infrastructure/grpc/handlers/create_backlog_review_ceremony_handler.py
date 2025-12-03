"""CreateBacklogReviewCeremony gRPC handler."""

import logging

import grpc

from planning.application.usecases import CreateBacklogReviewCeremonyUseCase
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.gen import planning_pb2
from planning.infrastructure.mappers.backlog_review_ceremony_protobuf_mapper import (
    BacklogReviewCeremonyProtobufMapper,
)

logger = logging.getLogger(__name__)


async def create_backlog_review_ceremony_handler(
    request: planning_pb2.CreateBacklogReviewCeremonyRequest,
    context,
    use_case: CreateBacklogReviewCeremonyUseCase,
) -> planning_pb2.CreateBacklogReviewCeremonyResponse:
    """Handle CreateBacklogReviewCeremony RPC."""
    try:
        logger.info(f"CreateBacklogReviewCeremony: created_by={request.created_by}")

        created_by = UserName(request.created_by)
        story_ids = tuple(StoryId(sid) for sid in request.story_ids)

        ceremony = await use_case.execute(
            created_by=created_by,
            story_ids=story_ids,
        )

        ceremony_pb = BacklogReviewCeremonyProtobufMapper.to_protobuf(ceremony)

        return planning_pb2.CreateBacklogReviewCeremonyResponse(
            success=True,
            message=f"Ceremony created: {ceremony.ceremony_id.value}",
            ceremony=ceremony_pb,
        )

    except ValueError as e:
        error_message = str(e)
        logger.warning(f"CreateBacklogReviewCeremony validation error: {error_message}")
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        return planning_pb2.CreateBacklogReviewCeremonyResponse(
            success=False,
            message=error_message,
        )

    except Exception as e:
        error_message = f"Internal error: {e}"
        logger.error(f"CreateBacklogReviewCeremony error: {error_message}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return planning_pb2.CreateBacklogReviewCeremonyResponse(
            success=False,
            message=error_message,
        )



