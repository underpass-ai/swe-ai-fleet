"""RejectReviewPlan gRPC handler."""

import logging

import grpc

from planning.application.usecases import RejectReviewPlanUseCase, CeremonyNotFoundError
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.gen import planning_pb2

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

        await use_case.execute(ceremony_id, story_id, rejected_by, rejection_reason)

        return planning_pb2.RejectReviewPlanResponse(
            success=True,
            message=f"Plan rejected for story {request.story_id}",
        )

    except CeremonyNotFoundError as e:
        logger.warning(f"Ceremony not found: {e}")
        context.set_code(grpc.StatusCode.NOT_FOUND)
        return planning_pb2.RejectReviewPlanResponse(
            success=False,
            message=str(e),
        )

    except ValueError as e:
        error_message = str(e)
        logger.warning(f"RejectReviewPlan validation error: {error_message}")
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        return planning_pb2.RejectReviewPlanResponse(
            success=False,
            message=error_message,
        )

    except Exception as e:
        error_message = f"Internal error: {e}"
        logger.error(f"RejectReviewPlan error: {error_message}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return planning_pb2.RejectReviewPlanResponse(
            success=False,
            message=error_message,
        )



