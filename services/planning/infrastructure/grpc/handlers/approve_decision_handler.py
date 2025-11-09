"""ApproveDecision gRPC handler."""

import logging

import grpc

from planning.application.usecases.approve_decision_usecase import ApproveDecisionUseCase
from planning.domain.value_objects.decision_id import DecisionId
from planning.domain.value_objects.story_id import StoryId
from planning.gen import planning_pb2

logger = logging.getLogger(__name__)


async def approve_decision(
    request: planning_pb2.ApproveDecisionRequest,
    context,
    use_case: ApproveDecisionUseCase,
) -> planning_pb2.ApproveDecisionResponse:
    """Handle ApproveDecision RPC."""
    try:
        logger.info(f"ApproveDecision: story_id={request.story_id}, decision_id={request.decision_id}")

        story_id = StoryId(request.story_id)
        decision_id = DecisionId(request.decision_id)

        await use_case.execute(
            story_id=story_id,
            decision_id=decision_id,
            approved_by=request.approved_by,
        )

        return planning_pb2.ApproveDecisionResponse(
            success=True,
            message=f"Decision approved: {decision_id.value}",
        )

    except ValueError as e:
        logger.warning(f"ApproveDecision validation error: {e}")
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        return planning_pb2.ApproveDecisionResponse(success=False, message=str(e))

    except Exception as e:
        logger.error(f"ApproveDecision error: {e}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return planning_pb2.ApproveDecisionResponse(success=False, message=f"Internal error: {e}")

