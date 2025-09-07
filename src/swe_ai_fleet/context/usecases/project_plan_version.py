# src/swe_ai_fleet/context/usecases/project_plan_version.py
from dataclasses import dataclass
from typing import Any

from swe_ai_fleet.context.domain.plan_version import PlanVersion
from swe_ai_fleet.context.ports.graph_command_port import GraphCommandPort


@dataclass
class ProjectPlanVersionUseCase:
    writer: GraphCommandPort

    def execute(self, payload: dict[str, Any]) -> None:
        # payload: {case_id, plan_id, version}
        plan_version = PlanVersion.from_payload(payload)
        self.writer.upsert_entity("PlanVersion", plan_version.plan_id, 
                                  plan_version.to_graph_properties())
        
        relationship = plan_version.get_relationship_to_case()
        self.writer.relate(relationship.src_id, relationship.rel_type, relationship.dst_id,
                           src_labels=relationship.src_labels, dst_labels=relationship.dst_labels)
