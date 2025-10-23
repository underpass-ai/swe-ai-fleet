"""Adapter for creating Deliberate councils."""

from __future__ import annotations

from typing import Any

from services.orchestrator.domain.ports import CouncilFactoryPort


class DeliberateCouncilFactoryAdapter(CouncilFactoryPort):
    """Adapter for creating Deliberate (peer deliberation) councils.
    
    This adapter implements the CouncilFactoryPort by using the legacy
    Deliberate use case. It handles the late import to avoid circular
    dependencies.
    """
    
    def __init__(self):
        """Initialize the adapter.
        
        Imports are done at initialization to avoid repeated imports
        while still being lazy enough to avoid circular dependencies.
        """
        # Import at adapter creation time (lazy but once)
        from core.orchestrator.usecases.peer_deliberation_usecase import Deliberate
        
        self._deliberate_class = Deliberate
    
    def create_council(self, agents: list[Any], tooling: Any, rounds: int) -> Any:
        """Create a Deliberate council instance.
        
        Args:
            agents: List of agent instances
            tooling: Scoring/tooling component
            rounds: Number of deliberation rounds
            
        Returns:
            Deliberate council instance
            
        Raises:
            RuntimeError: If council creation fails
        """
        try:
            # Create Deliberate council
            council = self._deliberate_class(
                agents=agents,
                tooling=tooling,
                rounds=rounds,
            )
            
            return council
        except Exception as e:
            raise RuntimeError(
                f"Failed to create Deliberate council with {len(agents)} agents: {e}"
            ) from e

