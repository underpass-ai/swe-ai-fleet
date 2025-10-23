"""Domain entity for task specifications."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TaskSpec:
    """Domain entity representing a task execution specification.
    
    This encapsulates the configuration needed to execute a task,
    including tool selection, arguments, environment, and timeout.
    """
    
    tool: str
    args: list[str]
    env: dict[str, str]
    timeout_sec: int
    
    @classmethod
    def create_simple_task(cls, task_title: str, timeout_sec: int = 60) -> TaskSpec:
        """Create a simple task specification for basic operations.
        
        Args:
            task_title: The title or description of the task
            timeout_sec: Timeout in seconds for task execution
            
        Returns:
            A TaskSpec configured for basic task execution
        """
        return cls(
            tool="echo",
            args=[f"Working on {task_title}"],
            env={},
            timeout_sec=timeout_sec,
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert the task specification to a dictionary format."""
        return {
            "tool": self.tool,
            "args": self.args,
            "env": self.env,
            "timeout_sec": self.timeout_sec,
        }
