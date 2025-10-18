"""Domain model for agent tasks (Aggregate Root)."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentTask:
    """
    Tarea asignada a un agente (Aggregate Root / Entity).
    
    Este es el AGGREGATE ROOT que encapsula toda la información
    necesaria para que un agente ejecute una tarea.
    
    A diferencia de los Value Objects (frozen), este es mutable
    porque representa una entidad que tiene ciclo de vida.
    """
    task_id: str
    task_description: str
    context: str = ""
    constraints: dict[str, Any] = field(default_factory=dict)
    diversity: bool = False
    
    @classmethod
    def create(
        cls,
        task_id: str,
        task_description: str,
        context: str = "",
        constraints: dict[str, Any] | None = None,
        diversity: bool = False,
    ) -> "AgentTask":
        """
        Factory method para crear una tarea.
        
        Args:
            task_id: Unique task identifier
            task_description: Description of the task
            context: Additional context for the task
            constraints: Task constraints (rubric, requirements, metadata, etc.)
            diversity: Whether to increase diversity in responses
            
        Returns:
            AgentTask instance
        """
        return cls(
            task_id=task_id,
            task_description=task_description,
            context=context,
            constraints=constraints or {},
            diversity=diversity,
        )
    
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
    
    def to_dict(self) -> dict[str, Any]:
        """
        Convertir a diccionario para serialización.
        
        Returns:
            Dictionary representation
        """
        return {
            "task_id": self.task_id,
            "task_description": self.task_description,
            "context": self.context,
            "constraints": self.constraints,
            "diversity": self.diversity,
        }

