# core/context/usecases/project_case.py
from dataclasses import dataclass
from typing import Any

from core.context.domain.case import Case
from core.context.ports.graph_command_port import GraphCommandPort


@dataclass
class ProjectCaseUseCase:
    writer: GraphCommandPort

    def execute(self, payload: dict[str, Any]) -> None:
        # payload: {case_id, name?}
        case = Case.from_payload(payload)
        self.writer.upsert_entity("Case", case.case_id, case.to_graph_properties())
