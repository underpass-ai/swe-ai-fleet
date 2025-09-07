# src/swe_ai_fleet/context/usecases/project_decision.py
from dataclasses import dataclass
from typing import Any

from swe_ai_fleet.context.domain.decision import Decision
from swe_ai_fleet.context.ports.graph_command_port import GraphCommandPort


@dataclass
class ProjectDecisionUseCase:
    writer: GraphCommandPort

    def execute(self, payload: dict[str, Any]) -> None:
        # payload: {node_id, kind?, summary?, sub_id?}
        decision = Decision.from_payload(payload)
        self.writer.upsert_entity("Decision", decision.node_id, decision.to_graph_properties())
        
        if decision.affects_subtask():
            self.writer.relate(decision.node_id, "AFFECTS", decision.sub_id,
                               src_labels=["Decision"], dst_labels=["Subtask"])
