"""StartPlanningCeremony gRPC handler.

Forwards to Planning Ceremony Processor when PLANNING_CEREMONY_PROCESSOR_URL is set.
Distinct from Backlog Review: this starts a step-based ceremony (definition_name, steps)
in the ceremony engine.
"""

import logging

from planning.application.ports.planning_ceremony_processor_port import (
    PlanningCeremonyProcessorError,
)
from planning.application.usecases.start_planning_ceremony_via_processor_usecase import (
    StartPlanningCeremonyViaProcessorUseCase,
)
from planning.gen import planning_pb2

import grpc

logger = logging.getLogger(__name__)


async def start_planning_ceremony_handler(
    request: planning_pb2.StartPlanningCeremonyRequest,
    context,
    use_case: StartPlanningCeremonyViaProcessorUseCase | None,
) -> planning_pb2.StartPlanningCeremonyResponse:
    """Handle StartPlanningCeremony RPC.

    When use_case is None (PLANNING_CEREMONY_PROCESSOR_URL not set), returns
    FAILED_PRECONDITION. Otherwise forwards to the processor.
    """
    if use_case is None:
        logger.warning("StartPlanningCeremony called but processor not configured")
        context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
        context.set_details("Planning Ceremony Processor not configured (PLANNING_CEREMONY_PROCESSOR_URL)")
        return planning_pb2.StartPlanningCeremonyResponse(
            instance_id="",
            status="",
            message="Planning Ceremony Processor not configured",
        )

    ceremony_id = (request.ceremony_id or "").strip()
    definition_name = (request.definition_name or "").strip()
    story_id = (request.story_id or "").strip()
    requested_by = (request.requested_by or "").strip()
    step_ids = list(request.step_ids) if request.step_ids else []

    if not ceremony_id:
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        context.set_details("ceremony_id is required")
        return planning_pb2.StartPlanningCeremonyResponse(
            instance_id="",
            status="",
            message="ceremony_id is required",
        )
    if not definition_name:
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        context.set_details("definition_name is required")
        return planning_pb2.StartPlanningCeremonyResponse(
            instance_id="",
            status="",
            message="definition_name is required",
        )
    if not story_id:
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        context.set_details("story_id is required")
        return planning_pb2.StartPlanningCeremonyResponse(
            instance_id="",
            status="",
            message="story_id is required",
        )
    if not requested_by:
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        context.set_details("requested_by is required")
        return planning_pb2.StartPlanningCeremonyResponse(
            instance_id="",
            status="",
            message="requested_by is required",
        )
    if not step_ids:
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        context.set_details("step_ids is required and cannot be empty")
        return planning_pb2.StartPlanningCeremonyResponse(
            instance_id="",
            status="",
            message="step_ids is required",
        )

    try:
        correlation_id = request.correlation_id or None
        inputs = dict(request.inputs) if request.inputs else None

        instance_id = await use_case.execute(
            ceremony_id=ceremony_id,
            definition_name=definition_name,
            story_id=story_id,
            step_ids=tuple(step_ids),
            requested_by=requested_by,
            correlation_id=correlation_id,
            inputs=inputs,
        )
        return planning_pb2.StartPlanningCeremonyResponse(
            instance_id=instance_id,
            status="accepted",
            message="Planning ceremony started",
        )
    except PlanningCeremonyProcessorError as e:
        logger.warning("StartPlanningCeremony processor error: %s", e)
        context.set_code(grpc.StatusCode.UNAVAILABLE)
        return planning_pb2.StartPlanningCeremonyResponse(
            instance_id="",
            status="",
            message=str(e),
        )
    except Exception as e:
        logger.exception("StartPlanningCeremony internal error: %s", e)
        context.set_code(grpc.StatusCode.INTERNAL)
        return planning_pb2.StartPlanningCeremonyResponse(
            instance_id="",
            status="",
            message=f"Internal error: {e}",
        )
