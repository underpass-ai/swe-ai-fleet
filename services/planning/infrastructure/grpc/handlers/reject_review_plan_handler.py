"""RejectReviewPlan gRPC handler."""

import logging

from planning.application.usecases import CeremonyNotFoundError, RejectReviewPlanUseCase
from planning.domain.value_objects.actors.user_name import UserName
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


async def reject_review_plan_handler(
    request: planning_pb2.RejectReviewPlanRequest,
    context,
    use_case: RejectReviewPlanUseCase,
) -> planning_pb2.RejectReviewPlanResponse:
    """Handle RejectReviewPlan RPC (Human-in-the-Loop)."""
    try:
        logger.info(
            f"RejectReviewPlan: ceremony_id={request.ceremony_id}, "
            f"story_id={request.story_id}"
        )

        ceremony_id = BacklogReviewCeremonyId(request.ceremony_id)
        story_id = StoryId(request.story_id)
        rejected_by = UserName(request.rejected_by)
        rejection_reason = request.rejection_reason

        ceremony = await use_case.execute(ceremony_id, story_id, rejected_by, rejection_reason)
        status_counts: dict[str, int] = {}
        for review_result in ceremony.review_results:
            status_raw = getattr(review_result.approval_status, "value", review_result.approval_status)
            status = str(status_raw)
            status_counts[status] = status_counts.get(status, 0) + 1
        logger.info(
            "RejectReviewPlan success: ceremony_id=%s story_id=%s rejected_by=%s status=%s "
            "review_results=%d status_counts=%s",
            ceremony_id.value,
            story_id.value,
            request.rejected_by,
            ceremony.status.value,
            len(ceremony.review_results),
            status_counts,
        )

        return ResponseProtobufMapper.reject_review_plan_response(
            success=True,
            message=f"Plan rejected for story {request.story_id}",
            ceremony=ceremony,
        )

    except CeremonyNotFoundError as e:
        logger.warning(f"Ceremony not found: {e}")
        context.set_code(grpc.StatusCode.NOT_FOUND)
        context.set_details(str(e))
        return ResponseProtobufMapper.reject_review_plan_response(
            success=False,
            message=str(e),
        )

    except ValueError as e:
        error_message = str(e)
        logger.warning(f"RejectReviewPlan validation error: {error_message}")
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        context.set_details(error_message)
        return ResponseProtobufMapper.reject_review_plan_response(
            success=False,
            message=error_message,
        )

    except Exception as e:
        error_message = f"Internal error: {e}"
        logger.error(f"RejectReviewPlan error: {error_message}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        context.set_details(error_message)
        return ResponseProtobufMapper.reject_review_plan_response(
            success=False,
            message=error_message,
        )




