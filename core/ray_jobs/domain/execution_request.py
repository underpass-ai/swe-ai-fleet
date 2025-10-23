"""Domain model for execution request."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ExecutionRequest:
    """
    Request para ejecutar un agente (Value Object).
    
    Agrupa todos los parámetros necesarios para ejecutar
    un agente en una tarea específica.
    """
    task_id: str
    task_description: str
    constraints: dict[str, Any] = field(default_factory=dict)
    diversity: bool = False
    
    @classmethod
    def create(
        cls,
        task_id: str,
        task_description: str,
        constraints: dict[str, Any] | None = None,
        diversity: bool = False,
    ) -> "ExecutionRequest":
        """
        Factory method para crear execution request.
        
        Args:
            task_id: Unique task identifier
            task_description: Description of the task
            constraints: Task constraints (rubric, requirements, context, metadata, etc.)
            diversity: Whether to increase diversity in responses
            
        Returns:
            ExecutionRequest instance
        """
        return cls(
            task_id=task_id,
            task_description=task_description,
            constraints=constraints or {},
            diversity=diversity,
        )
    
    def to_agent_task(self) -> "AgentTask":
        """
        Convertir a AgentTask (Aggregate Root).
        
        Returns:
            AgentTask instance
        """
        from .agent_task import AgentTask
        
        return AgentTask.create(
            task_id=self.task_id,
            task_description=self.task_description,
            context=self.constraints.get("context", ""),
            constraints=self.constraints,
            diversity=self.diversity,
        )
    
    def get_context(self) -> str:
        """Get context from constraints."""
        return self.constraints.get("context", "")
    
    def get_rubric(self) -> str:
        """Get rubric from constraints."""
        return self.constraints.get("rubric", "")
    
    def get_requirements(self) -> list[str]:
        """Get requirements from constraints."""
        return self.constraints.get("requirements", [])
    
    def get_metadata(self) -> dict[str, Any]:
        """Get metadata from constraints."""
        return self.constraints.get("metadata", {})
    
    def get_story_id(self) -> str:
        """Get story_id from constraints."""
        return self.constraints.get("story_id", "")
    
    def get_plan_id(self) -> str:
        """Get plan_id from constraints."""
        return self.constraints.get("plan_id", "")
    
    def get_timeout(self) -> int:
        """Get timeout from constraints."""
        return self.constraints.get("timeout", 60)

