# src/swe_ai_fleet/context/usecases/project_case.py
from dataclasses import dataclass
from typing import Dict, Any
from swe_ai_fleet.context.ports.graph_command_port import GraphCommandPort

@dataclass
class ProjectCaseUseCase:
    writer: GraphCommandPort

    def execute(self, payload: Dict[str, Any]) -> None:
        # payload: {case_id, name?}
        case_id = payload["case_id"]
        name = payload.get("name", "")
        self.writer.upsert_entity("Case", case_id, {"name": name})
