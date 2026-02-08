"""gRPC servicer for Planning Ceremony Processor."""

import json
from datetime import timezone

import grpc

from core.ceremony_engine.domain.entities.ceremony_instance import CeremonyInstance
from services.planning_ceremony_processor.application.usecases.get_planning_ceremony_instance_usecase import (
    GetPlanningCeremonyInstanceUseCase,
)
from services.planning_ceremony_processor.application.usecases.list_planning_ceremony_instances_usecase import (
    ListPlanningCeremonyInstancesUseCase,
)
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

    def __init__(
        self,
        start_use_case: StartPlanningCeremonyUseCase,
        get_use_case: GetPlanningCeremonyInstanceUseCase,
        list_use_case: ListPlanningCeremonyInstancesUseCase,
    ) -> None:
        if not start_use_case:
            raise ValueError("start_use_case is required (fail-fast)")
        if not get_use_case:
            raise ValueError("get_use_case is required (fail-fast)")
        if not list_use_case:
            raise ValueError("list_use_case is required (fail-fast)")
        if planning_ceremony_pb2 is None or planning_ceremony_pb2_grpc is None:
            raise RuntimeError(
                "Planning ceremony protobuf stubs not available. "
                "Generate protobuf stubs before instantiating servicer."
            )
        self._start_use_case = start_use_case
        self._get_use_case = get_use_case
        self._list_use_case = list_use_case

    @staticmethod
    def _split_instance_id(instance_id: str) -> tuple[str, str]:
        parts = instance_id.rsplit(":", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return instance_id, ""

    @staticmethod
    def _derive_status(instance: CeremonyInstance) -> str:
        if instance.is_terminal() or instance.is_completed():
            return "COMPLETED"
        return "IN_PROGRESS"

    @staticmethod
    def _to_iso8601(value) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()

    @staticmethod
    def _stringify_step_output(output: object) -> str:
        if isinstance(output, str):
            return output
        return json.dumps(output, ensure_ascii=True, sort_keys=True)

    @classmethod
    def _to_proto_instance(cls, instance: CeremonyInstance):
        ceremony_id, story_id = cls._split_instance_id(instance.instance_id)
        step_status = {
            entry.step_id.value: entry.status.value for entry in instance.step_status.entries
        }
        step_outputs = {
            entry.step_id.value: cls._stringify_step_output(entry.output)
            for entry in instance.step_outputs.entries
        }
        return planning_ceremony_pb2.PlanningCeremonyInstance(
            instance_id=instance.instance_id,
            ceremony_id=ceremony_id,
            story_id=story_id,
            definition_name=instance.definition.name,
            current_state=instance.current_state,
            status=cls._derive_status(instance),
            correlation_id=instance.correlation_id,
            step_status=step_status,
            step_outputs=step_outputs,
            created_at=cls._to_iso8601(instance.created_at),
            updated_at=cls._to_iso8601(instance.updated_at),
        )

    @staticmethod
    def _optional_field(request, field_name: str) -> str | None:
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
            instance = await self._start_use_case.execute(dto)
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

    async def GetPlanningCeremonyInstance(self, request, context):
        try:
            instance_id = (request.instance_id or "").strip()
            if not instance_id:
                raise ValueError("instance_id cannot be empty")

            instance = await self._get_use_case.execute(instance_id)
            if instance is None:
                return planning_ceremony_pb2.GetPlanningCeremonyInstanceResponse(
                    success=False,
                    message=f"Ceremony instance not found: {instance_id}",
                )

            return planning_ceremony_pb2.GetPlanningCeremonyInstanceResponse(
                ceremony=self._to_proto_instance(instance),
                success=True,
                message="Ceremony instance retrieved",
            )
        except ValueError as exc:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(exc))
            return planning_ceremony_pb2.GetPlanningCeremonyInstanceResponse(
                success=False,
                message=str(exc),
            )
        except Exception as exc:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return planning_ceremony_pb2.GetPlanningCeremonyInstanceResponse(
                success=False,
                message=f"Internal error: {exc}",
            )

    async def ListPlanningCeremonyInstances(self, request, context):
        try:
            limit = request.limit if request.limit > 0 else 100
            offset = request.offset if request.offset >= 0 else 0
            state_filter = self._optional_field(request, "state_filter")
            definition_filter = self._optional_field(request, "definition_filter")
            story_id = self._optional_field(request, "story_id")

            instances, total_count = await self._list_use_case.execute(
                limit=limit,
                offset=offset,
                state_filter=state_filter,
                definition_filter=definition_filter,
                story_id=story_id,
            )

            return planning_ceremony_pb2.ListPlanningCeremonyInstancesResponse(
                ceremonies=[self._to_proto_instance(instance) for instance in instances],
                total_count=total_count,
                success=True,
                message=f"Found {len(instances)} ceremony instances",
            )
        except ValueError as exc:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(exc))
            return planning_ceremony_pb2.ListPlanningCeremonyInstancesResponse(
                ceremonies=[],
                total_count=0,
                success=False,
                message=str(exc),
            )
        except Exception as exc:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return planning_ceremony_pb2.ListPlanningCeremonyInstancesResponse(
                ceremonies=[],
                total_count=0,
                success=False,
                message=f"Internal error: {exc}",
            )
