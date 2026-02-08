"""Planning Ceremony Processor gRPC adapter (thin client).

Implements PlanningCeremonyProcessorPort. Calls planning_ceremony_processor
StartPlanningCeremony gRPC (fire-and-forget).
"""

import logging

import grpc
from planning.application.ports.planning_ceremony_processor_port import (
    PlanningCeremonyInstanceData,
    PlanningCeremonyProcessorError,
    PlanningCeremonyProcessorPort,
)
from planning.gen import planning_ceremony_pb2, planning_ceremony_pb2_grpc

logger = logging.getLogger(__name__)


class PlanningCeremonyProcessorAdapter(PlanningCeremonyProcessorPort):
    """gRPC adapter for Planning Ceremony Processor."""

    def __init__(self, grpc_address: str) -> None:
        if not grpc_address or not grpc_address.strip():
            raise ValueError("grpc_address cannot be empty")
        self._address = grpc_address
        self._channel = grpc.aio.insecure_channel(grpc_address)
        self._stub = planning_ceremony_pb2_grpc.PlanningCeremonyProcessorStub(
            self._channel
        )
        logger.info("PlanningCeremonyProcessorAdapter initialized: %s", grpc_address)

    async def start_planning_ceremony(
        self,
        ceremony_id: str,
        definition_name: str,
        story_id: str,
        step_ids: tuple[str, ...],
        requested_by: str,
        correlation_id: str | None = None,
        inputs: dict[str, str] | None = None,
    ) -> str:
        req = planning_ceremony_pb2.StartPlanningCeremonyRequest(
            ceremony_id=ceremony_id,
            definition_name=definition_name,
            story_id=story_id,
            step_ids=list(step_ids),
            requested_by=requested_by,
            correlation_id=correlation_id or "",
            inputs=inputs or {},
        )
        try:
            resp = await self._stub.StartPlanningCeremony(req)
            return resp.instance_id or f"{ceremony_id}:{story_id}"
        except grpc.RpcError as e:
            raise PlanningCeremonyProcessorError(
                f"Planning Ceremony Processor gRPC failed: {e.details()}"
            ) from e

    @staticmethod
    def _to_instance_data(message) -> PlanningCeremonyInstanceData:
        return PlanningCeremonyInstanceData(
            instance_id=message.instance_id,
            ceremony_id=message.ceremony_id,
            story_id=message.story_id,
            definition_name=message.definition_name,
            current_state=message.current_state,
            status=message.status,
            correlation_id=message.correlation_id,
            step_status=dict(message.step_status),
            step_outputs=dict(message.step_outputs),
            created_at=message.created_at,
            updated_at=message.updated_at,
        )

    async def get_planning_ceremony(
        self,
        instance_id: str,
    ) -> PlanningCeremonyInstanceData | None:
        req = planning_ceremony_pb2.GetPlanningCeremonyInstanceRequest(
            instance_id=instance_id,
        )
        try:
            resp = await self._stub.GetPlanningCeremonyInstance(req)
            if not resp.success or not resp.ceremony or not resp.ceremony.instance_id:
                return None
            return self._to_instance_data(resp.ceremony)
        except grpc.RpcError as e:
            raise PlanningCeremonyProcessorError(
                f"Planning Ceremony Processor gRPC failed: {e.details()}"
            ) from e

    async def list_planning_ceremonies(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        state_filter: str | None = None,
        definition_filter: str | None = None,
        story_id: str | None = None,
    ) -> tuple[list[PlanningCeremonyInstanceData], int]:
        req_kwargs = {
            "limit": limit,
            "offset": offset,
        }
        if state_filter:
            req_kwargs["state_filter"] = state_filter
        if definition_filter:
            req_kwargs["definition_filter"] = definition_filter
        if story_id:
            req_kwargs["story_id"] = story_id

        req = planning_ceremony_pb2.ListPlanningCeremonyInstancesRequest(**req_kwargs)
        try:
            resp = await self._stub.ListPlanningCeremonyInstances(req)
            if not resp.success:
                return [], 0
            instances = [self._to_instance_data(item) for item in resp.ceremonies]
            return instances, int(resp.total_count or 0)
        except grpc.RpcError as e:
            raise PlanningCeremonyProcessorError(
                f"Planning Ceremony Processor gRPC failed: {e.details()}"
            ) from e
