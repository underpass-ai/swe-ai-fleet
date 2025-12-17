"""GetBacklogReviewCeremony gRPC handler."""

import logging

from planning.application.usecases import GetBacklogReviewCeremonyUseCase
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.gen import planning_pb2
from planning.infrastructure.mappers.response_protobuf_mapper import (
    ResponseProtobufMapper,
)

import grpc

logger = logging.getLogger(__name__)


async def get_backlog_review_ceremony_handler(
    request: planning_pb2.GetBacklogReviewCeremonyRequest,
    context,
    use_case: GetBacklogReviewCeremonyUseCase,
) -> planning_pb2.BacklogReviewCeremonyResponse:
    """Handle GetBacklogReviewCeremony RPC."""
    try:
        logger.info(f"GetBacklogReviewCeremony: ceremony_id={request.ceremony_id}")

        ceremony_id = BacklogReviewCeremonyId(request.ceremony_id)
        ceremony = await use_case.execute(ceremony_id)

        if not ceremony:
            return ResponseProtobufMapper.get_backlog_review_ceremony_response(
                success=False,
                message=f"Ceremony not found: {request.ceremony_id}",
            )

        return ResponseProtobufMapper.get_backlog_review_ceremony_response(
            success=True,
            message=f"Ceremony retrieved: {ceremony.ceremony_id.value}",
            ceremony=ceremony,
        )

    except Exception as e:
        error_message = f"Internal error: {e}"
        logger.error(f"GetBacklogReviewCeremony error: {error_message}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return ResponseProtobufMapper.get_backlog_review_ceremony_response(
            success=False,
            message=error_message,
        )

