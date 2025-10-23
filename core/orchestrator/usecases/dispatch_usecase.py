"""Dispatch use case."""

from typing import Any

from ..config_module.system_config import SystemConfig
from ..domain import ArchitectSelectorService, TaskConstraints
from .peer_deliberation_usecase import Deliberate


class Orchestrate:
    """Use case for orchestrating the complete task execution workflow.
    
    This use case orchestrates the process of routing tasks to the right council,
    executing deliberation, and selecting the best proposal through the architect.
    """
    
    def __init__(
        self, config: SystemConfig, councils: dict[str, Deliberate], architect: ArchitectSelectorService
    ) -> None:
        """Initialize the orchestration use case.
        
        Args:
            config: System configuration
            councils: Dictionary mapping role names to deliberation use cases
            architect: Architect selector service for choosing the best proposal
        """
        self._config = config
        self._councils = councils
        self._architect = architect

    async def execute(self, role: str, task: str, constraints: TaskConstraints) -> dict[str, Any]:
        """Execute the orchestration process for a task.
        
        Args:
            role: The role/council to handle the task
            task: The task description to execute
            constraints: Task constraints and rubrics
            
        Returns:
            Dictionary containing the winner and all candidates
        """
        council = self._councils[role]
        ranked = await council.execute(task, constraints)
        return self._architect.choose(ranked, constraints)
