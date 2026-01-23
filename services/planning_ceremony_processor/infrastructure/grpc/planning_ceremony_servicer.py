"""gRPC servicer for Planning Ceremony Processor."""

import grpc

from services.planning_ceremony_processor.application.dto.start_planning_ceremony_request_dto import (
    StartPlanningCeremonyRequestDTO,
)
from services.planning_ceremony_processor.application.usecases.start_planning_ceremony_usecase import (
    StartPlanningCeremonyUseCase,
)

try:
    from services.planning_ceremony_processor.gen import (
        planning_ceremony_pb2,
        planning_ceremony_pb2_grpc,
    )
except ImportError:
    planning_ceremony_pb2 = None
    planning_ceremony_pb2_grpc = None

_BaseServicer = (
    planning_ceremony_pb2_grpc.PlanningCeremonyProcessorServicer
    if planning_ceremony_pb2_grpc
    else object
)


class PlanningCeremonyProcessorServicer(_BaseServicer):
    """gRPC adapter that starts ceremony executions."""

    def __init__(self, use_case: StartPlanningCeremonyUseCase) -> None:
        if not use_case:
            raise ValueError("use_case is required (fail-fast)")
        if planning_ceremony_pb2 is None or planning_ceremony_pb2_grpc is None:
            raise RuntimeError(
                "Planning ceremony protobuf stubs not available. "
                "Generate protobuf stubs before instantiating servicer."
            )
        self._use_case = use_case

    async def StartPlanningCeremony(self, request, context):
        try:
            dto = StartPlanningCeremonyRequestDTO(
                ceremony_id=request.ceremony_id,
                definition_name=request.definition_name,
                story_id=request.story_id,
                correlation_id=request.correlation_id or None,
                inputs=dict(request.inputs),
                step_ids=tuple(request.step_ids),
                requested_by=request.requested_by,
            )
            instance = await self._use_case.execute(dto)
            return planning_ceremony_pb2.StartPlanningCeremonyResponse(
                instance_id=instance.instance_id,
                status="accepted",
                message="ceremony execution started",
            )
        except ValueError as exc:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(exc))
            return planning_ceremony_pb2.StartPlanningCeremonyResponse()
        except Exception as exc:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return planning_ceremony_pb2.StartPlanningCeremonyResponse()
