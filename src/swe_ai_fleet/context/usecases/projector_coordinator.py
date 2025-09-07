# src/swe_ai_fleet/context/usecases/projector_coordinator.py
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from swe_ai_fleet.context.ports.graph_command_port import GraphCommandPort

from .project_case import ProjectCaseUseCase
from .project_decision import ProjectDecisionUseCase
from .project_plan_version import ProjectPlanVersionUseCase
from .project_subtask import ProjectSubtaskUseCase
from .update_subtask_status import UpdateSubtaskStatusUseCase


@dataclass
class ProjectorCoordinator:
    writer: GraphCommandPort

    def __post_init__(self):
        self.handlers: dict[str, Callable[[dict[str, Any]], None]] = {
            "case.created": ProjectCaseUseCase(self.writer).execute,
            "plan.versioned": ProjectPlanVersionUseCase(self.writer).execute,
            "subtask.created": ProjectSubtaskUseCase(self.writer).execute,
            "subtask.status_changed": UpdateSubtaskStatusUseCase(self.writer).execute,
            "decision.made": ProjectDecisionUseCase(self.writer).execute,
        }

    def handle(self, event_type: str, payload: dict[str, Any]) -> bool:
        fn = self.handlers.get(event_type)
        if not fn:
            return False
        fn(payload)
        return True
