# src/swe_ai_fleet/context/usecases/project_subtask.py
from dataclasses import dataclass
from typing import Any

from swe_ai_fleet.context.ports.graph_command_port import GraphCommandPort


@dataclass
class ProjectSubtaskUseCase:
    writer: GraphCommandPort

    def execute(self, payload: dict[str, Any]) -> None:
        # payload: {plan_id, sub_id, title?, type?}
        plan_id = payload["plan_id"]
        sub_id = payload["sub_id"]
        title = payload.get("title", "")
        typ = payload.get("type", "task")
        self.writer.upsert_entity("Subtask", sub_id, {"title": title, "type": typ})
        self.writer.relate(plan_id, "HAS_SUBTASK", sub_id,
                           src_labels=["PlanVersion"], dst_labels=["Subtask"])
