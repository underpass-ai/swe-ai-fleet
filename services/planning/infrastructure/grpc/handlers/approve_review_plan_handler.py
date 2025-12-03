"""ApproveReviewPlan gRPC handler."""

import logging

import grpc

from planning.application.usecases import ApproveReviewPlanUseCase, CeremonyNotFoundError
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.gen import planning_pb2
from planning.infrastructure.mappers.plan_protobuf_mapper import PlanProtobufMapper

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
        approved_by = UserName(request.approved_by)

        # Execute use case
        plan = await use_case.execute(ceremony_id, story_id, approved_by)

        # Convert Plan to protobuf
        plan_pb = PlanProtobufMapper.to_protobuf(plan)

        return planning_pb2.ApproveReviewPlanResponse(
            success=True,
            message=f"Plan approved and created: {plan.plan_id.value}",
            plan=plan_pb,
        )

    except CeremonyNotFoundError as e:
        logger.warning(f"Ceremony not found: {e}")
        context.set_code(grpc.StatusCode.NOT_FOUND)
        return planning_pb2.ApproveReviewPlanResponse(
            success=False,
            message=str(e),
        )

    except ValueError as e:
        error_message = str(e)
        logger.warning(f"ApproveReviewPlan validation error: {error_message}")
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        return planning_pb2.ApproveReviewPlanResponse(
            success=False,
            message=error_message,
        )

    except Exception as e:
        error_message = f"Internal error: {e}"
        logger.error(f"ApproveReviewPlan error: {error_message}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return planning_pb2.ApproveReviewPlanResponse(
            success=False,
            message=error_message,
        )



