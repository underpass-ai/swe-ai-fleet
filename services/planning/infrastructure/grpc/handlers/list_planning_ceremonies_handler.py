"""ListPlanningCeremonies gRPC handler."""

import logging

import grpc

from planning.application.ports.planning_ceremony_processor_port import (
    PlanningCeremonyProcessorError,
)
from planning.application.usecases.list_planning_ceremonies_via_processor_usecase import (
    ListPlanningCeremoniesViaProcessorUseCase,
)
from planning.gen import planning_pb2
from planning.infrastructure.mappers.planning_ceremony_instance_protobuf_mapper import (
    PlanningCeremonyInstanceProtobufMapper,
)

logger = logging.getLogger(__name__)


def _optional_filter(request, field_name: str) -> str | None:
    if hasattr(request, "HasField"):
        try:
            if request.HasField(field_name):
                value = getattr(request, field_name, "")
                value = value.strip() if isinstance(value, str) else value
                return value or None
            return None
        except ValueError:
            return None

    value = getattr(request, field_name, "")
    if isinstance(value, str):
        value = value.strip()
    return value or None


async def list_planning_ceremonies_handler(
    request: planning_pb2.ListPlanningCeremoniesRequest,
    context,
    use_case: ListPlanningCeremoniesViaProcessorUseCase | None,
) -> planning_pb2.ListPlanningCeremoniesResponse:
    """Handle ListPlanningCeremonies RPC."""
    if use_case is None:
        logger.warning("ListPlanningCeremonies called but processor not configured")
        context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
        context.set_details(
            "Planning Ceremony Processor not configured (PLANNING_CEREMONY_PROCESSOR_URL)"
        )
        return planning_pb2.ListPlanningCeremoniesResponse(
            ceremonies=[],
            total_count=0,
            success=False,
            message="Planning Ceremony Processor not configured",
        )

    try:
        limit = request.limit if request.limit > 0 else 100
        offset = request.offset if request.offset >= 0 else 0
        state_filter = _optional_filter(request, "state_filter")
        definition_filter = _optional_filter(request, "definition_filter")
        story_id = _optional_filter(request, "story_id")

        instances, total_count = await use_case.execute(
            limit=limit,
            offset=offset,
            state_filter=state_filter,
            definition_filter=definition_filter,
            story_id=story_id,
        )

        return planning_pb2.ListPlanningCeremoniesResponse(
            ceremonies=[
                PlanningCeremonyInstanceProtobufMapper.to_protobuf(instance)
                for instance in instances
            ],
            total_count=total_count,
            success=True,
            message=f"Found {len(instances)} planning ceremony instances",
        )
    except PlanningCeremonyProcessorError as e:
        logger.warning("ListPlanningCeremonies processor error: %s", e)
        context.set_code(grpc.StatusCode.UNAVAILABLE)
        return planning_pb2.ListPlanningCeremoniesResponse(
            ceremonies=[],
            total_count=0,
            success=False,
            message=str(e),
        )
    except Exception as e:
        logger.exception("ListPlanningCeremonies internal error: %s", e)
        context.set_code(grpc.StatusCode.INTERNAL)
        return planning_pb2.ListPlanningCeremoniesResponse(
            ceremonies=[],
            total_count=0,
            success=False,
            message=f"Internal error: {e}",
        )
