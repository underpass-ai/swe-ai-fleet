"""GetPlanningCeremony gRPC handler."""

import logging

import grpc

from planning.application.ports.planning_ceremony_processor_port import (
    PlanningCeremonyProcessorError,
)
from planning.application.usecases.get_planning_ceremony_via_processor_usecase import (
    GetPlanningCeremonyViaProcessorUseCase,
)
from planning.gen import planning_pb2
from planning.infrastructure.mappers.planning_ceremony_instance_protobuf_mapper import (
    PlanningCeremonyInstanceProtobufMapper,
)

logger = logging.getLogger(__name__)


async def get_planning_ceremony_handler(
    request: planning_pb2.GetPlanningCeremonyRequest,
    context,
    use_case: GetPlanningCeremonyViaProcessorUseCase | None,
) -> planning_pb2.GetPlanningCeremonyResponse:
    """Handle GetPlanningCeremony RPC."""
    if use_case is None:
        logger.warning("GetPlanningCeremony called but processor not configured")
        context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
        context.set_details(
            "Planning Ceremony Processor not configured (PLANNING_CEREMONY_PROCESSOR_URL)"
        )
        return planning_pb2.GetPlanningCeremonyResponse(
            success=False,
            message="Planning Ceremony Processor not configured",
        )

    instance_id = (request.instance_id or "").strip()
    if not instance_id:
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        context.set_details("instance_id is required")
        return planning_pb2.GetPlanningCeremonyResponse(
            success=False,
            message="instance_id is required",
        )

    try:
        instance = await use_case.execute(instance_id=instance_id)
        if instance is None:
            return planning_pb2.GetPlanningCeremonyResponse(
                success=False,
                message=f"Ceremony instance not found: {instance_id}",
            )

        return planning_pb2.GetPlanningCeremonyResponse(
            ceremony=PlanningCeremonyInstanceProtobufMapper.to_protobuf(instance),
            success=True,
            message="Planning ceremony retrieved",
        )
    except PlanningCeremonyProcessorError as e:
        logger.warning("GetPlanningCeremony processor error: %s", e)
        context.set_code(grpc.StatusCode.UNAVAILABLE)
        return planning_pb2.GetPlanningCeremonyResponse(
            success=False,
            message=str(e),
        )
    except ValueError as e:
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        return planning_pb2.GetPlanningCeremonyResponse(
            success=False,
            message=str(e),
        )
    except Exception as e:
        logger.exception("GetPlanningCeremony internal error: %s", e)
        context.set_code(grpc.StatusCode.INTERNAL)
        return planning_pb2.GetPlanningCeremonyResponse(
            success=False,
            message=f"Internal error: {e}",
        )
