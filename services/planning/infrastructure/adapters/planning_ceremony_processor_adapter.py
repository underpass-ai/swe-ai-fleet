"""Planning Ceremony Processor gRPC adapter (thin client).

Implements PlanningCeremonyProcessorPort. Calls planning_ceremony_processor
StartPlanningCeremony gRPC (fire-and-forget).
"""

import logging

import grpc
from planning.application.ports.planning_ceremony_processor_port import (
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
