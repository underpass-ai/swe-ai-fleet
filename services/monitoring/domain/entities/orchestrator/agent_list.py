"""Agent list value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .agent_info import AgentInfo
    from .agent_summary import AgentSummary


@dataclass(frozen=True)
class AgentList:
    """Value object representing a list of agents.
    
    This immutable value object encapsulates a collection of AgentInfo objects
    and provides domain-specific operations on the collection.
    """
    
    agents: list[AgentInfo]
    
    @classmethod
    def create(cls, agents: list[AgentInfo]) -> AgentList:
        """Create AgentList with validation.
        
        Args:
            agents: List of AgentInfo objects.
            
        Returns:
            AgentList instance
            
        Raises:
            ValueError: If agents list is invalid.
        """
        # Validate that all agents are AgentInfo instances
        for i, agent in enumerate(agents):
            if not hasattr(agent, 'agent_id') or not hasattr(agent, 'role') or not hasattr(agent, 'status'):
                raise ValueError(f"Agent at index {i} is not a valid AgentInfo instance")
        
        return cls(agents=agents)
    
    @classmethod
    def create_empty(cls) -> AgentList:
        """Create empty AgentList.
        
        Returns:
            Empty AgentList instance
        """
        return cls(agents=[])
    
    def count(self) -> int:
        """Get the number of agents in the list.
        
        Tell, Don't Ask: Tell the list to count its agents.
        
        Returns:
            Number of agents in the list.
        """
        return len(self.agents)
    
    def is_empty(self) -> bool:
        """Check if the agent list is empty.
        
        Tell, Don't Ask: Tell the list to check if it's empty.
        
        Returns:
            True if the list is empty, False otherwise.
        """
        return len(self.agents) == 0
    
    def get_agents_by_role(self, role: str) -> list[AgentInfo]:
        """Get all agents with a specific role.
        
        Tell, Don't Ask: Tell the list to filter agents by role.
        
        Args:
            role: Role to filter by.
            
        Returns:
            List of agents with the specified role.
        """
        return [agent for agent in self.agents if agent.role == role]
    
    def get_agents_by_status(self, status: str) -> list[AgentInfo]:
        """Get all agents with a specific status.
        
        Tell, Don't Ask: Tell the list to filter agents by status.
        
        Args:
            status: Status to filter by.
            
        Returns:
            List of agents with the specified status.
        """
        return [agent for agent in self.agents if agent.status == status]
    
    def get_agent_by_id(self, agent_id: str) -> AgentInfo | None:
        """Get agent by ID.
        
        Args:
            agent_id: Agent identifier to search for
            
        Returns:
            AgentInfo if found, None otherwise
        """
        for agent in self.agents:
            if agent.agent_id == agent_id:
                return agent
        return None
    
    def has_agent(self, agent_id: str) -> bool:
        """Check if agent exists by ID.
        
        Args:
            agent_id: Agent identifier to check
            
        Returns:
            True if agent exists, False otherwise
        """
        return self.get_agent_by_id(agent_id) is not None
    
    def get_ready_agents(self) -> list[AgentInfo]:
        """Get all ready agents.
        
        Tell, Don't Ask: Tell the list to get ready agents.
        
        Returns:
            List of agents that are ready.
        """
        return [agent for agent in self.agents if agent.is_ready()]
    
    def get_busy_agents(self) -> list[AgentInfo]:
        """Get all busy agents.
        
        Tell, Don't Ask: Tell the list to get busy agents.
        
        Returns:
            List of agents that are busy.
        """
        return [agent for agent in self.agents if agent.is_busy()]
    
    def get_offline_agents(self) -> list[AgentInfo]:
        """Get all offline agents.
        
        Tell, Don't Ask: Tell the list to get offline agents.
        
        Returns:
            List of agents that are offline.
        """
        return [agent for agent in self.agents if agent.is_offline()]
    
    def to_list(self) -> list[AgentInfo]:
        """Convert to regular list.
        
        Returns:
            List of AgentInfo objects.
        """
        return list(self.agents)
    
    def to_dict_list(self) -> list[dict[str, str]]:
        """Convert to list of dictionaries.
        
        Returns:
            List of dictionaries representing each agent.
        """
        return [agent.to_dict() for agent in self.agents]
    
    def get_status_summary(self, agent_summary_factory: type[AgentSummary]) -> AgentSummary:
        """Get summary of agent statuses in the list.
        
        Tell, Don't Ask: Tell AgentList to provide status summary.
        
        Args:
            agent_summary_factory: Factory class for creating AgentSummary instances
        
        Returns:
            AgentSummary with status counts
        """
        summary = {}
        for agent in self.agents:
            status = agent.status
            summary[status] = summary.get(status, 0) + 1
        
        return agent_summary_factory.from_status_dict(summary)
