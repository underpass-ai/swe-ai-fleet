"""Task domain object."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Task:
    """Domain object representing a task to be executed.
    
    Encapsulates a task with its description and any associated metadata.
    """
    
    description: str
    id: str | None = None
    priority: int = 0
    
    def __str__(self) -> str:
        """String representation of the task."""
        return self.description
    
    def __len__(self) -> int:
        """Length of the task description."""
        return len(self.description)
    
    @property
    def is_empty(self) -> bool:
        """Check if the task description is empty."""
        return not self.description.strip()
    
    @classmethod
    def from_string(cls, description: str, task_id: str | None = None) -> Task:
        """Create a Task from a string description.
        
        Args:
            description: The task description
            task_id: Optional task identifier
            
        Returns:
            Task object
        """
        return cls(description=description, id=task_id)
