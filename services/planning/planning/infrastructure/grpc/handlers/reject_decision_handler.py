"""RejectDecision gRPC handler."""

import logging

import grpc

from planning.application.usecases.reject_decision_usecase import RejectDecisionUseCase
from planning.domain.value_objects.decision_id import DecisionId
from planning.domain.value_objects.story_id import StoryId
from planning.gen import planning_pb2
from planning.infrastructure.grpc.mappers.response_mapper import ResponseMapper

logger = logging.getLogger(__name__)


async def reject_decision(
    request: planning_pb2.RejectDecisionRequest,
    context,
    use_case: RejectDecisionUseCase,
) -> planning_pb2.RejectDecisionResponse:
    """Handle RejectDecision RPC."""
    try:
        logger.info(f"RejectDecision: story_id={request.story_id}, decision_id={request.decision_id}")

        story_id = StoryId(request.story_id)
        decision_id = DecisionId(request.decision_id)

        await use_case.execute(
            story_id=story_id,
            decision_id=decision_id,
            rejected_by=request.rejected_by,
            reason=request.reason,
        )

        return ResponseMapper.reject_decision_response(
            success=True,
            message=f"Decision rejected: {decision_id.value}",
        )

    except ValueError as e:
        logger.warning(f"RejectDecision validation error: {e}")
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        return ResponseMapper.reject_decision_response(success=False, message=str(e))

    except Exception as e:
        logger.error(f"RejectDecision error: {e}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return ResponseMapper.reject_decision_response(success=False, message=f"Internal error: {e}")

