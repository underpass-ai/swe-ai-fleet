# src/swe_ai_fleet/context/usecases/project_decision.py
from dataclasses import dataclass
from typing import Dict, Any
from swe_ai_fleet.context.ports.graph_command_port import GraphCommandPort

@dataclass
class ProjectDecisionUseCase:
    writer: GraphCommandPort

    def execute(self, payload: Dict[str, Any]) -> None:
        # payload: {node_id, kind?, summary?, sub_id?}
        node_id = payload["node_id"]
        kind = payload.get("kind", "")
        summary = payload.get("summary", "")
        self.writer.upsert_entity("Decision", node_id, {"kind": kind, "summary": summary})
        if "sub_id" in payload:
            self.writer.relate(node_id, "AFFECTS", payload["sub_id"],
                               src_labels=["Decision"], dst_labels=["Subtask"])
