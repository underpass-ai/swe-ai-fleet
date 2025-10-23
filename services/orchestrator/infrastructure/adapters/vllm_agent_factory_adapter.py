"""Adapter for creating vLLM agents."""

from __future__ import annotations

from typing import Any

from services.orchestrator.domain.entities import AgentConfig
from services.orchestrator.domain.ports import AgentFactoryPort


class VLLMAgentFactoryAdapter(AgentFactoryPort):
    """Adapter for creating vLLM agents using AgentFactory.
    
    This adapter implements the AgentFactoryPort by using the legacy
    AgentFactory infrastructure component. It handles the late import
    to avoid circular dependencies.
    """
    
    def __init__(self):
        """Initialize the adapter.
        
        Imports are done at initialization to avoid repeated imports
        while still being lazy enough to avoid circular dependencies.
        """
        # Import at adapter creation time (lazy but once)
        from core.orchestrator.domain.agents.agent_factory import AgentFactory
        
        self._agent_factory = AgentFactory
    
    def create_agent(self, config: AgentConfig) -> Any:
        """Create a vLLM agent from configuration.
        
        Args:
            config: AgentConfig domain entity
            
        Returns:
            Agent instance created by AgentFactory
            
        Raises:
            RuntimeError: If agent creation fails
        """
        try:
            # Convert domain entity to dict for legacy AgentFactory
            config_dict = config.to_dict()
            
            # Use AgentFactory to create agent
            agent = self._agent_factory.create_agent(**config_dict)
            
            return agent
        except Exception as e:
            raise RuntimeError(
                f"Failed to create agent with config {config.agent_id}: {e}"
            ) from e

