"""CreateBacklogReviewCeremony gRPC handler."""

import logging

from planning.application.usecases import CreateBacklogReviewCeremonyUseCase
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.gen import planning_pb2
from planning.infrastructure.mappers.response_protobuf_mapper import (
    ResponseProtobufMapper,
)

import grpc

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
        # Handle story_ids - repeated fields are always present as a list (may be empty)
        story_ids_list = request.story_ids if request.story_ids else []
        story_ids = tuple(StoryId(sid) for sid in story_ids_list)

        ceremony = await use_case.execute(
            created_by=created_by,
            story_ids=story_ids,
        )

        return ResponseProtobufMapper.create_backlog_review_ceremony_response(
            success=True,
            message=f"Ceremony created: {ceremony.ceremony_id.value}",
            ceremony=ceremony,
        )

    except ValueError as e:
        error_message = str(e)
        logger.warning(f"CreateBacklogReviewCeremony validation error: {error_message}")
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        return ResponseProtobufMapper.create_backlog_review_ceremony_response(
            success=False,
            message=error_message,
        )

    except Exception as e:
        error_message = f"Internal error: {e}"
        logger.error(f"CreateBacklogReviewCeremony error: {error_message}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return ResponseProtobufMapper.create_backlog_review_ceremony_response(
            success=False,
            message=error_message,
        )






