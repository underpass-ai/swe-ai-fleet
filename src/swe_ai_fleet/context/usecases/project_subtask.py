# src/swe_ai_fleet/context/usecases/project_subtask.py
from dataclasses import dataclass
from typing import Any

from swe_ai_fleet.context.domain.subtask import Subtask
from swe_ai_fleet.context.ports.graph_command_port import GraphCommandPort


@dataclass
class ProjectSubtaskUseCase:
    writer: GraphCommandPort

    def execute(self, payload: dict[str, Any]) -> None:
        # payload: {plan_id, sub_id, title?, type?}
        subtask = Subtask.from_payload(payload)
        self.writer.upsert_entity("Subtask", subtask.sub_id, subtask.to_graph_properties())

        relationship = subtask.get_relationship_to_plan()
        self.writer.relate(
            relationship.src_id,
            relationship.rel_type,
            relationship.dst_id,
            src_labels=relationship.src_labels,
            dst_labels=relationship.dst_labels,
        )
