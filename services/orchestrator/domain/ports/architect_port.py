"""Port for architect selection operations."""

from __future__ import annotations

from typing import Any, Protocol


class ArchitectPort(Protocol):
    """Port for architect agent selection and management.
    
    This port defines the interface for selecting and managing
    the architect agent, abstracting infrastructure details.
    
    Implementations might use:
    - Static architect selection
    - Dynamic architect selection based on task
    - Multiple architect strategies
    """
    
    def select_architect(self, task: Any) -> Any:
        """Select an architect for the given task.
        
        Args:
            task: Task that needs an architect
            
        Returns:
            Selected architect agent
        """
        ...
    
    def get_default_architect(self) -> Any:
        """Get the default architect agent.
        
        Returns:
            Default architect instance
        """
        ...

