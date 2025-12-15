"""AddAgentDeliberation gRPC handler."""

import logging
from datetime import UTC, datetime

import grpc
from planning.application.dto import StoryReviewResultDTO
from planning.application.usecases import ProcessStoryReviewResultUseCase
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.statuses.backlog_review_role import (
    BacklogReviewRole,
)
from planning.gen import planning_pb2  # type: ignore[import-not-found]
from planning.infrastructure.mappers.response_protobuf_mapper import (
    ResponseProtobufMapper,
)

logger = logging.getLogger(__name__)


async def add_agent_deliberation_handler(
    request: planning_pb2.AddAgentDeliberationRequest,
    context,
    use_case: ProcessStoryReviewResultUseCase,
) -> planning_pb2.AddAgentDeliberationResponse:
    """Handle AddAgentDeliberation RPC."""
    try:
        logger.info(
            f"AddAgentDeliberation: ceremony={request.ceremony_id}, "
            f"story={request.story_id}, role={request.role}, agent={request.agent_id}"
        )

        # Convert protobuf → domain VOs
        ceremony_id = BacklogReviewCeremonyId(request.ceremony_id)
        story_id = StoryId(request.story_id)
        role = BacklogReviewRole(request.role)

        # Parse proposal (can be dict or string)
        import json

        proposal = request.proposal
        if isinstance(proposal, str):
            try:
                proposal = json.loads(proposal)
            except json.JSONDecodeError:
                # Keep proposal as original string if not valid JSON
                pass

        # Parse timestamp
        reviewed_at = datetime.now(UTC)
        if request.reviewed_at:
            try:
                reviewed_at = datetime.fromisoformat(
                    request.reviewed_at.replace("Z", "+00:00")
                )
            except Exception:
                reviewed_at = datetime.now(UTC)

        # Create DTO
        review_result_dto = StoryReviewResultDTO(
            ceremony_id=ceremony_id,
            story_id=story_id,
            role=role,
            agent_id=request.agent_id,
            feedback=request.feedback,
            proposal=proposal,
            reviewed_at=reviewed_at,
        )

        # Execute use case
        ceremony = await use_case.execute(review_result_dto)

        return ResponseProtobufMapper.add_agent_deliberation_response(
            success=True,
            message=f"Agent deliberation added to ceremony {ceremony_id.value}",
            ceremony=ceremony,
        )

    except ValueError as e:
        error_message = str(e)
        logger.warning(f"AddAgentDeliberation validation error: {error_message}")
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        return ResponseProtobufMapper.add_agent_deliberation_response(
            success=False,
            message=error_message,
        )

    except Exception as e:
        error_message = f"Internal error: {e}"
        logger.error(f"AddAgentDeliberation error: {error_message}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return ResponseProtobufMapper.add_agent_deliberation_response(
            success=False,
            message=error_message,
        )
