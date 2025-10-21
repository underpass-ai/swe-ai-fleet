"""Port for council creation."""

from __future__ import annotations

from typing import Any, Protocol


class CouncilFactoryPort(Protocol):
    """Port for creating council instances.
    
    This port defines the interface for council creation,
    abstracting the infrastructure details of how councils are instantiated.
    
    Implementations might use:
    - Deliberate (peer deliberation)
    - Different council strategies
    - Mock councils (for testing)
    """
    
    def create_council(self, agents: list[Any], tooling: Any, rounds: int) -> Any:
        """Create a council instance.
        
        Args:
            agents: List of agent instances
            tooling: Tooling/scoring component for the council
            rounds: Number of deliberation rounds
            
        Returns:
            Council instance
            
        Raises:
            RuntimeError: If council creation fails
        """
        ...

