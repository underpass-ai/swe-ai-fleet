"""ApproveReviewPlan gRPC handler."""

import logging

from planning.application.usecases import ApproveReviewPlanUseCase, CeremonyNotFoundError
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.review.plan_approval import PlanApproval
from planning.gen import planning_pb2
from planning.infrastructure.mappers.response_protobuf_mapper import (
    ResponseProtobufMapper,
)

import grpc

logger = logging.getLogger(__name__)


async def approve_review_plan_handler(
    request: planning_pb2.ApproveReviewPlanRequest,
    context,
    use_case: ApproveReviewPlanUseCase,
) -> planning_pb2.ApproveReviewPlanResponse:
    """Handle ApproveReviewPlan RPC (Human-in-the-Loop)."""
    try:
        logger.info(
            f"ApproveReviewPlan: ceremony_id={request.ceremony_id}, "
            f"story_id={request.story_id}, approved_by={request.approved_by}"
        )

        ceremony_id = BacklogReviewCeremonyId(request.ceremony_id)
        story_id = StoryId(request.story_id)

        # Create PlanApproval value object (domain layer)
        # Encapsulates PO approval context with validation
        approval = PlanApproval(
            approved_by=UserName(request.approved_by),
            po_notes=request.po_notes,
            po_concerns=request.po_concerns if request.po_concerns else None,
            priority_adjustment=request.priority_adjustment if request.priority_adjustment else None,
            po_priority_reason=request.po_priority_reason if request.po_priority_reason else None,
        )

        # Execute use case with approval value object
        plan, ceremony = await use_case.execute(
            ceremony_id=ceremony_id,
            story_id=story_id,
            approval=approval,
        )
        status_counts: dict[str, int] = {}
        for review_result in ceremony.review_results:
            status_raw = getattr(review_result.approval_status, "value", review_result.approval_status)
            status = str(status_raw)
            status_counts[status] = status_counts.get(status, 0) + 1
        logger.info(
            "ApproveReviewPlan success: ceremony_id=%s story_id=%s plan_id=%s status=%s "
            "review_results=%d status_counts=%s",
            ceremony_id.value,
            story_id.value,
            plan.plan_id.value,
            ceremony.status.value,
            len(ceremony.review_results),
            status_counts,
        )

        return ResponseProtobufMapper.approve_review_plan_response(
            success=True,
            message=f"Plan approved and created: {plan.plan_id.value}",
            ceremony=ceremony,
            plan_id=plan.plan_id.value,
        )

    except CeremonyNotFoundError as e:
        logger.warning(f"Ceremony not found: {e}")
        context.set_code(grpc.StatusCode.NOT_FOUND)
        return ResponseProtobufMapper.approve_review_plan_response(
            success=False,
            message=str(e),
        )

    except ValueError as e:
        error_message = str(e)
        logger.warning(f"ApproveReviewPlan validation error: {error_message}")
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        return ResponseProtobufMapper.approve_review_plan_response(
            success=False,
            message=error_message,
        )

    except Exception as e:
        error_message = f"Internal error: {e}"
        logger.error(f"ApproveReviewPlan error: {error_message}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return ResponseProtobufMapper.approve_review_plan_response(
            success=False,
            message=error_message,
        )





