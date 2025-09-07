# src/swe_ai_fleet/context/usecases/update_subtask_status.py
from dataclasses import dataclass
from typing import Any

from swe_ai_fleet.context.domain.subtask import Subtask
from swe_ai_fleet.context.ports.graph_command_port import GraphCommandPort


@dataclass
class UpdateSubtaskStatusUseCase:
    writer: GraphCommandPort

    def execute(self, payload: dict[str, Any]) -> None:
        # payload: {sub_id, status}
        subtask = Subtask.from_status_update_payload(payload)
        self.writer.upsert_entity("Subtask", subtask.sub_id, subtask.to_graph_properties())
