"""Complete and Cancel Backlog Review Ceremony gRPC handlers."""

import logging

from planning.application.usecases import (
    CancelBacklogReviewCeremonyUseCase,
    CeremonyNotFoundError,
    CompleteBacklogReviewCeremonyUseCase,
)
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


async def complete_backlog_review_ceremony_handler(
    request: planning_pb2.CompleteBacklogReviewCeremonyRequest,
    context,
    use_case: CompleteBacklogReviewCeremonyUseCase,
) -> planning_pb2.CompleteBacklogReviewCeremonyResponse:
    """Handle CompleteBacklogReviewCeremony RPC."""
    try:
        logger.info(f"CompleteBacklogReviewCeremony: ceremony_id={request.ceremony_id}")

        ceremony_id = BacklogReviewCeremonyId(request.ceremony_id)
        completed_by = UserName(request.completed_by)

        ceremony = await use_case.execute(ceremony_id, completed_by)

        return ResponseProtobufMapper.complete_backlog_review_ceremony_response(
            success=True,
            message=f"Ceremony completed: {ceremony.ceremony_id.value}",
            ceremony=ceremony,
        )

    except CeremonyNotFoundError as e:
        logger.warning(f"Ceremony not found: {e}")
        context.set_code(grpc.StatusCode.NOT_FOUND)
        return ResponseProtobufMapper.complete_backlog_review_ceremony_response(
            success=False,
            message=str(e),
        )

    except ValueError as e:
        error_message = str(e)
        logger.warning(f"CompleteBacklogReviewCeremony validation error: {error_message}")
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        return ResponseProtobufMapper.complete_backlog_review_ceremony_response(
            success=False,
            message=error_message,
        )

    except Exception as e:
        error_message = f"Internal error: {e}"
        logger.error(f"CompleteBacklogReviewCeremony error: {error_message}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return ResponseProtobufMapper.complete_backlog_review_ceremony_response(
            success=False,
            message=error_message,
        )


async def cancel_backlog_review_ceremony_handler(
    request: planning_pb2.CancelBacklogReviewCeremonyRequest,
    context,
    use_case: CancelBacklogReviewCeremonyUseCase,
) -> planning_pb2.CancelBacklogReviewCeremonyResponse:
    """Handle CancelBacklogReviewCeremony RPC."""
    try:
        logger.info(f"CancelBacklogReviewCeremony: ceremony_id={request.ceremony_id}")

        ceremony_id = BacklogReviewCeremonyId(request.ceremony_id)
        cancelled_by = UserName(request.cancelled_by)

        ceremony = await use_case.execute(ceremony_id, cancelled_by)

        return ResponseProtobufMapper.cancel_backlog_review_ceremony_response(
            success=True,
            message=f"Ceremony cancelled: {ceremony.ceremony_id.value}",
            ceremony=ceremony,
        )

    except CeremonyNotFoundError as e:
        logger.warning(f"Ceremony not found: {e}")
        context.set_code(grpc.StatusCode.NOT_FOUND)
        return ResponseProtobufMapper.cancel_backlog_review_ceremony_response(
            success=False,
            message=str(e),
        )

    except ValueError as e:
        error_message = str(e)
        logger.warning(f"CancelBacklogReviewCeremony validation error: {error_message}")
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        return ResponseProtobufMapper.cancel_backlog_review_ceremony_response(
            success=False,
            message=error_message,
        )

    except Exception as e:
        error_message = f"Internal error: {e}"
        logger.error(f"CancelBacklogReviewCeremony error: {error_message}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return ResponseProtobufMapper.cancel_backlog_review_ceremony_response(
            success=False,
            message=error_message,
        )






