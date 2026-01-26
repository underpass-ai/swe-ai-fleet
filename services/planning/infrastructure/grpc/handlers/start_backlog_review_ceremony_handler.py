"""StartBacklogReviewCeremony gRPC handler."""

import asyncio
import logging

from planning.application.usecases import CeremonyNotFoundError, StartBacklogReviewCeremonyUseCase
from planning.application.usecases.start_planning_ceremony_via_processor_usecase import (
    StartPlanningCeremonyViaProcessorUseCase,
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

# Default definition and step for thin-client fire-and-forget to Planning Ceremony Processor.
_DEFAULT_DEFINITION_NAME = "dummy_ceremony"
_DEFAULT_STEP_IDS = ("process_step",)


def _schedule_start_planning_ceremony(
    planning_ceremony_processor_uc: StartPlanningCeremonyViaProcessorUseCase,
    ceremony_id: str,
    story_id: str,
    requested_by: str,
) -> None:
    """Fire-and-forget StartPlanningCeremony via processor (asyncio task)."""
    async def _run() -> None:
        try:
            instance_id = await planning_ceremony_processor_uc.execute(
                ceremony_id=ceremony_id,
                definition_name=_DEFAULT_DEFINITION_NAME,
                story_id=story_id,
                step_ids=_DEFAULT_STEP_IDS,
                requested_by=requested_by,
                correlation_id=f"{ceremony_id}:{story_id}",
            )
            logger.info(
                "StartPlanningCeremony (thin client) fired: instance_id=%s",
                instance_id,
            )
        except Exception as e:
            logger.warning(
                "StartPlanningCeremony (thin client) failed for %s:%s: %s",
                ceremony_id,
                story_id,
                e,
                exc_info=True,
            )

    asyncio.create_task(_run())


async def start_backlog_review_ceremony_handler(
    request: planning_pb2.StartBacklogReviewCeremonyRequest,
    context,
    use_case: StartBacklogReviewCeremonyUseCase,
    planning_ceremony_processor_uc: StartPlanningCeremonyViaProcessorUseCase | None = None,
) -> planning_pb2.StartBacklogReviewCeremonyResponse:
    """Handle StartBacklogReviewCeremony RPC.

    WARNING: This is a LONG-RUNNING operation (minutes).
    Each story review involves multiple deliberations with councils.

    When planning_ceremony_processor_uc is set, also calls Planning Ceremony Processor
    StartPlanningCeremony (fire-and-forget) per story.
    """
    try:
        logger.info(f"StartBacklogReviewCeremony: ceremony_id={request.ceremony_id}")

        ceremony_id = BacklogReviewCeremonyId(request.ceremony_id)
        started_by = UserName(request.started_by)

        # Execute use case (LONG-RUNNING)
        ceremony, total_deliberations = await use_case.execute(ceremony_id, started_by)

        # Optional thin client: fire-and-forget StartPlanningCeremony per story
        if planning_ceremony_processor_uc and ceremony.story_ids:
            for story_id in ceremony.story_ids:
                _schedule_start_planning_ceremony(
                    planning_ceremony_processor_uc=planning_ceremony_processor_uc,
                    ceremony_id=request.ceremony_id,
                    story_id=story_id.value,
                    requested_by=request.started_by,
                )

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

