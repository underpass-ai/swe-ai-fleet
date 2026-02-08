"""Mapper for PlanningCeremonyInstanceData -> protobuf message."""

from planning.application.ports.planning_ceremony_processor_port import (
    PlanningCeremonyInstanceData,
)
from planning.gen import planning_pb2


class PlanningCeremonyInstanceProtobufMapper:
    """Convert planning ceremony processor DTOs to planning protobuf messages."""

    @staticmethod
    def to_protobuf(
        data: PlanningCeremonyInstanceData,
    ) -> planning_pb2.PlanningCeremonyInstance:
        return planning_pb2.PlanningCeremonyInstance(
            instance_id=data.instance_id,
            ceremony_id=data.ceremony_id,
            story_id=data.story_id,
            definition_name=data.definition_name,
            current_state=data.current_state,
            status=data.status,
            correlation_id=data.correlation_id,
            step_status=data.step_status,
            step_outputs=data.step_outputs,
            created_at=data.created_at,
            updated_at=data.updated_at,
        )
