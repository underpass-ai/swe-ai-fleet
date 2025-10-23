"""Agent collection entity."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.orchestrator.config_module.vllm_config import VLLMConfig
    
    from .agent_config import AgentConfig


@dataclass
class AgentCollection:
    """Domain entity representing a collection of agents.
    
    Manages a collection of agents with their identifiers and provides
    operations for agent management and querying.
    
    Attributes:
        agents: List of agent instances
        agent_ids: List of agent identifiers
    """
    
    agents: list[Any] = field(default_factory=list)
    agent_ids: list[str] = field(default_factory=list)
    
    def add_agent(self, agent: Any, agent_id: str) -> None:
        """Add an agent to the collection.
        
        Args:
            agent: Agent instance to add
            agent_id: Unique identifier for the agent
            
        Raises:
            ValueError: If agent_id already exists in collection
        """
        if agent_id in self.agent_ids:
            raise ValueError(f"Agent with id {agent_id} already exists in collection")
        
        self.agents.append(agent)
        self.agent_ids.append(agent_id)
    
    def create_and_add_agents(
        self,
        role: str,
        num_agents: int,
        vllm_config: VLLMConfig,
        agent_factory: Callable[[AgentConfig], Any],
        custom_params: dict[str, Any] | None = None
    ) -> None:
        """Create and add multiple agents for a role.
        
        Applies "Tell, Don't Ask" principle by encapsulating agent creation logic
        within the collection. Uses AgentConfig.create() factory method.
        
        Args:
            role: Role name for the agents (e.g., "Coder", "Architect")
            num_agents: Number of agents to create
            vllm_config: VLLMConfig instance with base configuration
            agent_factory: Function that creates an agent from AgentConfig
            custom_params: Optional custom parameters to override defaults
            
        Example:
            >>> from core.orchestrator.config_module.vllm_config import VLLMConfig
            >>> vllm_config = VLLMConfig.from_env()
            >>> def create_agent(config: AgentConfig) -> Agent:
            ...     return Agent(config.to_dict())
            >>> collection.create_and_add_agents(
            ...     "Coder", 3, vllm_config, create_agent,
            ...     custom_params={"temperature": 0.9}
            ... )
        """
        # Import at runtime to avoid circular dependency
        from .agent_config import AgentConfig
        
        for i in range(num_agents):
            agent_id = f"agent-{role.lower()}-{i+1:03d}"
            
            # Use AgentConfig factory method to create configuration
            agent_config = AgentConfig.create(
                agent_id=agent_id,
                role=role,
                index=i,
                vllm_config=vllm_config,
                custom_params=custom_params
            )
            
            # Create agent using injected factory
            agent = agent_factory(agent_config)
            
            # Add to collection
            self.add_agent(agent, agent_id)
    
    def remove_agent(self, agent_id: str) -> None:
        """Remove an agent from the collection by ID.
        
        Args:
            agent_id: Identifier of the agent to remove
            
        Raises:
            ValueError: If agent_id not found in collection
        """
        if agent_id not in self.agent_ids:
            raise ValueError(f"Agent with id {agent_id} not found in collection")
        
        index = self.agent_ids.index(agent_id)
        self.agents.pop(index)
        self.agent_ids.pop(index)
    
    def get_agent_by_id(self, agent_id: str) -> Any:
        """Get an agent by its ID.
        
        Args:
            agent_id: Identifier of the agent to retrieve
            
        Returns:
            The agent instance
            
        Raises:
            ValueError: If agent_id not found in collection
        """
        if not self.has_agent(agent_id):
            raise ValueError(f"Agent with id {agent_id} not found in collection")
        
        index = self.agent_ids.index(agent_id)
        return self.agents[index]
    
    def has_agent(self, agent_id: str) -> bool:
        """Check if an agent exists in the collection.
        
        Args:
            agent_id: Identifier to check
            
        Returns:
            True if agent exists, False otherwise
        """
        return agent_id in self.agent_ids
    
    @property
    def count(self) -> int:
        """Get the number of agents in the collection."""
        return len(self.agents)
    
    @property
    def is_empty(self) -> bool:
        """Check if the collection is empty."""
        return self.count == 0
    
    def clear(self) -> None:
        """Remove all agents from the collection."""
        self.agents.clear()
        self.agent_ids.clear()
    
    def get_all_ids(self) -> list[str]:
        """Get a copy of all agent IDs.
        
        Returns:
            List of agent identifiers
        """
        return self.agent_ids.copy()
    
    def get_all_agents(self) -> list[Any]:
        """Get a copy of all agents.
        
        Returns:
            List of agent instances
        """
        return self.agents.copy()
    
    def to_dict(self) -> dict[str, Any]:
        """Convert collection to dictionary.
        
        Returns:
            Dictionary representation of the collection
        """
        return {
            "count": self.count,
            "agent_ids": self.agent_ids.copy(),
        }
    
    def __len__(self) -> int:
        """Get the number of agents in the collection."""
        return self.count
    
    def __contains__(self, agent_id: str) -> bool:
        """Check if an agent ID exists in the collection."""
        return self.has_agent(agent_id)
    
    def __iter__(self):
        """Iterate over agents in the collection."""
        return iter(self.agents)

