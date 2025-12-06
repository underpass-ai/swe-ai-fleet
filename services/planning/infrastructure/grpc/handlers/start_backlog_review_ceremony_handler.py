"""StartBacklogReviewCeremony gRPC handler."""

import logging

from planning.application.usecases import CeremonyNotFoundError, StartBacklogReviewCeremonyUseCase
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.gen import planning_pb2
from planning.infrastructure.mappers.response_protobuf_mapper import (
    ResponseProtobufMapper,
)

import grpc

logger = logging.getLogger(__name__)


async def start_backlog_review_ceremony_handler(
    request: planning_pb2.StartBacklogReviewCeremonyRequest,
    context,
    use_case: StartBacklogReviewCeremonyUseCase,
) -> planning_pb2.StartBacklogReviewCeremonyResponse:
    """Handle StartBacklogReviewCeremony RPC.

    WARNING: This is a LONG-RUNNING operation (minutes).
    Each story review involves multiple deliberations with councils.
    """
    try:
        logger.info(f"StartBacklogReviewCeremony: ceremony_id={request.ceremony_id}")

        ceremony_id = BacklogReviewCeremonyId(request.ceremony_id)
        started_by = UserName(request.started_by)

        # Execute use case (LONG-RUNNING)
        ceremony, total_deliberations = await use_case.execute(ceremony_id, started_by)

        return ResponseProtobufMapper.start_backlog_review_ceremony_response(
            success=True,
            message=f"Ceremony started: {total_deliberations} deliberations submitted",
            ceremony=ceremony,
            total_deliberations_submitted=total_deliberations,
        )

    except CeremonyNotFoundError as e:
        logger.warning(f"Ceremony not found: {e}")
        context.set_code(grpc.StatusCode.NOT_FOUND)
        return ResponseProtobufMapper.start_backlog_review_ceremony_response(
            success=False,
            message=str(e),
        )

    except ValueError as e:
        error_message = str(e)
        logger.warning(f"StartBacklogReviewCeremony validation error: {error_message}")
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        return ResponseProtobufMapper.start_backlog_review_ceremony_response(
            success=False,
            message=error_message,
        )

    except Exception as e:
        error_message = f"Internal error: {e}"
        logger.error(f"StartBacklogReviewCeremony error: {error_message}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return ResponseProtobufMapper.start_backlog_review_ceremony_response(
            success=False,
            message=error_message,
        )

