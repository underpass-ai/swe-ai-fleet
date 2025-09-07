# src/swe_ai_fleet/context/usecases/update_subtask_status.py
from dataclasses import dataclass
from typing import Any

from swe_ai_fleet.context.ports.graph_command_port import GraphCommandPort


@dataclass
class UpdateSubtaskStatusUseCase:
    writer: GraphCommandPort

    def execute(self, payload: dict[str, Any]) -> None:
        # payload: {sub_id, status}
        sub_id = payload["sub_id"]
        status = payload.get("status")
        self.writer.upsert_entity("Subtask", sub_id, {"last_status": status})
