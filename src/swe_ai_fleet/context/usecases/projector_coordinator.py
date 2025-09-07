# src/swe_ai_fleet/context/usecases/projector_coordinator.py
from dataclasses import dataclass
from typing import Dict, Any, Callable

from swe_ai_fleet.context.ports.graph_command_port import GraphCommandPort
from .project_case import ProjectCaseUseCase
from .project_plan_version import ProjectPlanVersionUseCase
from .project_subtask import ProjectSubtaskUseCase
from .update_subtask_status import UpdateSubtaskStatusUseCase
from .project_decision import ProjectDecisionUseCase

@dataclass
class ProjectorCoordinator:
    writer: GraphCommandPort

    def __post_init__(self):
        self.handlers: Dict[str, Callable[[Dict[str, Any]], None]] = {
            "case.created": ProjectCaseUseCase(self.writer).execute,
            "plan.versioned": ProjectPlanVersionUseCase(self.writer).execute,
            "subtask.created": ProjectSubtaskUseCase(self.writer).execute,
            "subtask.status_changed": UpdateSubtaskStatusUseCase(self.writer).execute,
            "decision.made": ProjectDecisionUseCase(self.writer).execute,
        }

    def handle(self, event_type: str, payload: Dict[str, Any]) -> bool:
        fn = self.handlers.get(event_type)
        if not fn:
            return False
        fn(payload)
        return True
