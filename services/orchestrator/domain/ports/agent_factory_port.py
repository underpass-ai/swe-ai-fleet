"""Port for agent creation."""

from __future__ import annotations

from typing import Any, Protocol

from services.orchestrator.domain.entities import AgentConfig


class AgentFactoryPort(Protocol):
    """Port for creating agent instances.
    
    This port defines the interface for agent creation,
    abstracting the infrastructure details of how agents are created.
    
    Implementations might use:
    - vLLM agents
    - Mock agents (for testing)
    - Remote agents
    """
    
    def create_agent(self, config: AgentConfig) -> Any:
        """Create an agent from configuration.
        
        Args:
            config: AgentConfig domain entity with agent configuration
            
        Returns:
            Agent instance
            
        Raises:
            RuntimeError: If agent creation fails
        """
        ...

