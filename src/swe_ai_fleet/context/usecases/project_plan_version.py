# src/swe_ai_fleet/context/usecases/project_plan_version.py
from dataclasses import dataclass
from typing import Any

from swe_ai_fleet.context.ports.graph_command_port import GraphCommandPort


@dataclass
class ProjectPlanVersionUseCase:
    writer: GraphCommandPort

    def execute(self, payload: dict[str, Any]) -> None:
        # payload: {case_id, plan_id, version}
        case_id = payload["case_id"]
        plan_id = payload["plan_id"]
        version = int(payload.get("version", 1))
        self.writer.upsert_entity("PlanVersion", plan_id, {"version": version})
        self.writer.relate(case_id, "HAS_PLAN", plan_id,
                           src_labels=["Case"], dst_labels=["PlanVersion"])
