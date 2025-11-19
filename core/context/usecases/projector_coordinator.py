# core/context/usecases/projector_coordinator.py
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from core.context.ports.graph_command_port import GraphCommandPort

from .project_decision import ProjectDecisionUseCase
from .project_plan_version import ProjectPlanVersionUseCase
from .project_story import ProjectStoryUseCase
from .project_task import ProjectTaskUseCase
from .update_task_status import UpdateTaskStatusUseCase


@dataclass
class ProjectorCoordinator:
    writer: GraphCommandPort

    def __post_init__(self):
        self.handlers: dict[str, Callable[[dict[str, Any]], None]] = {
            "case.created": ProjectStoryUseCase(self.writer).execute,  # Renamed from ProjectCaseUseCase
            "plan.versioned": ProjectPlanVersionUseCase(self.writer).execute,
            "subtask.created": ProjectTaskUseCase(self.writer).execute,  # Renamed from ProjectSubtaskUseCase
            "subtask.status_changed": UpdateTaskStatusUseCase(self.writer).execute,  # Renamed from UpdateSubtaskStatusUseCase
            "decision.made": ProjectDecisionUseCase(self.writer).execute,
        }

    def handle(self, event_type: str, payload: dict[str, Any]) -> bool:
        fn = self.handlers.get(event_type)
        if not fn:
            return False
        fn(payload)
        return True
