"""Adapter for architect selection operations."""

from __future__ import annotations

from typing import Any

from services.orchestrator.domain.ports import ArchitectPort


class ArchitectAdapter(ArchitectPort):
    """Adapter implementing architect selection.
    
    This adapter implements the ArchitectPort by delegating to the
    legacy ArchitectSelectorService infrastructure component.
    """
    
    def __init__(self):
        """Initialize the adapter.
        
        Imports architect components at adapter creation time to avoid
        circular dependencies while only importing once.
        """
        # Import at adapter creation time (lazy but once)
        from core.orchestrator.domain.agents.architect_agent import ArchitectAgent
        from core.orchestrator.domain.agents.services.architect_selector_service import (
            ArchitectSelectorService,
        )
        
        # Create default architect and selector service
        default_architect = ArchitectAgent()
        self._selector_service = ArchitectSelectorService(architect=default_architect)
    
    def select_architect(self, task: Any) -> Any:
        """Select an architect for the given task.
        
        Args:
            task: Task that needs an architect
            
        Returns:
            Selected architect agent
        """
        return self._selector_service.select_architect(task)
    
    def get_default_architect(self) -> Any:
        """Get the default architect agent.
        
        Returns:
            Default architect instance
        """
        # Access the architect from the selector service
        return self._selector_service.architect
    
    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attributes to the wrapped ArchitectSelectorService.
        
        This allows the adapter to be used as a drop-in replacement
        for the ArchitectSelectorService class.
        
        Args:
            name: Attribute name
            
        Returns:
            Attribute from wrapped ArchitectSelectorService instance
        """
        return getattr(self._selector_service, name)

