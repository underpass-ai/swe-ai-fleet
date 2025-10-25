"""Council information value object."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .agent_list import AgentList
from .agent_role import AgentRole
from .council_status import CouncilStatus

if TYPE_CHECKING:
    from .agent_info import AgentInfo
    from .agent_summary import AgentSummary


@dataclass(frozen=True)
class CouncilInfo:
    """Value object representing council information.
    
    A council is a group of agents working together on a specific role.
    This immutable value object encapsulates all information about a council
    in the orchestrator system. It follows the Value Object pattern from DDD.
    
    Attributes:
        council_id: Unique council identifier (e.g., "council-dev-001")
        role: Council role (e.g., "DEV", "QA", "ARCHITECT")
        emoji: Emoji representation for the role
        status: Council status (e.g., "active", "idle", "inactive")
        model: AI model used by agents in this council
        total_agents: Total number of agents in the council
        agents: AgentList of agents in this council
    """
    
    council_id: str
    role: str
    emoji: str
    status: str
    model: str
    total_agents: int
    agents: AgentList = field(default_factory=lambda: AgentList.create_empty())
    
    def __post_init__(self):
        """Validate council info after initialization."""
        # Convert agents list to AgentList if needed
        if isinstance(self.agents, list):
            object.__setattr__(self, 'agents', AgentList.create(self.agents))
        
        # Validate basic fields
        if not self.council_id or not self.council_id.strip():
            raise ValueError("Council ID cannot be empty")
        if not self.role or not self.role.strip():
            raise ValueError("Council role cannot be empty")
        if not self.emoji or not self.emoji.strip():
            raise ValueError("Council emoji cannot be empty")
        if not self.status or not self.status.strip():
            raise ValueError("Council status cannot be empty")
        if not self.model or not self.model.strip():
            raise ValueError("Council model cannot be empty")
        if self.total_agents < 0:
            raise ValueError("Total agents cannot be negative")
        
        # Use centralized validation
        AgentRole.validate_role(self.role)
        CouncilStatus.validate_status(self.status)
        
        # Validate agents consistency
        if self.agents.count() != self.total_agents:
            raise ValueError(
                f"Total agents ({self.total_agents}) does not match "
                f"actual agents count ({self.agents.count()})"
            )
        
        # Validate agents roles - Tell, Don't Ask
        for agent in self.agents.agents:
            agent.validate_role_consistency(self.role)
    
    def is_active(self) -> bool:
        """Check if council is active.
        
        Tell, Don't Ask: Tell council to check if it's active
        instead of asking for status and checking externally.
        
        Returns:
            True if council is active, False otherwise
        """
        return self.status == "active"
    
    def is_idle(self) -> bool:
        """Check if council is idle.
        
        Tell, Don't Ask: Tell council to check if it's idle.
        
        Returns:
            True if council is idle, False otherwise
        """
        return self.status == "idle"
    
    def is_offline(self) -> bool:
        """Check if council is offline.
        
        Tell, Don't Ask: Tell council to check if it's offline.
        
        Returns:
            True if council is offline, False otherwise
        """
        return self.status == "offline"
    
    def has_agents(self) -> bool:
        """Check if council has any agents.
        
        Tell, Don't Ask: Tell council to check if it has agents.
        
        Returns:
            True if council has agents, False otherwise
        """
        return not self.agents.is_empty()
    
    def get_ready_agents(self) -> list[AgentInfo]:
        """Get all ready agents in the council.
        
        Tell, Don't Ask: Tell council to provide ready agents.
        
        Returns:
            List of ready agents
        """
        return self.agents.get_ready_agents()
    
    def get_busy_agents(self) -> list[AgentInfo]:
        """Get all busy agents in the council.
        
        Tell, Don't Ask: Tell council to provide busy agents.
        
        Returns:
            List of busy agents
        """
        return self.agents.get_busy_agents()
    
    def get_offline_agents(self) -> list[AgentInfo]:
        """Get all offline agents in the council.
        
        Tell, Don't Ask: Tell council to provide offline agents.
        
        Returns:
            List of offline agents
        """
        return self.agents.get_offline_agents()
    
    def get_agent_by_id(self, agent_id: str) -> AgentInfo | None:
        """Get agent by ID.
        
        Tell, Don't Ask: Tell council to get agent by ID.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            AgentInfo if found, None otherwise
        """
        return self.agents.get_agent_by_id(agent_id)
    
    def has_agent(self, agent_id: str) -> bool:
        """Check if council has agent with given ID.
        
        Tell, Don't Ask: Tell council to check if it has agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            True if agent exists, False otherwise
        """
        return self.agents.has_agent(agent_id)
    
    def get_display_name(self) -> str:
        """Get human-readable display name for the council.
        
        Tell, Don't Ask: Tell council to provide its display name.
        
        Returns:
            Formatted display name (e.g., "DEV Council (3 agents)")
        """
        return f"{self.role} Council ({self.total_agents} agents)"
    
    def get_agent_summary(self, agent_summary_factory: type[AgentSummary]) -> AgentSummary:
        """Get summary of agent statuses in the council.
        
        Tell, Don't Ask: Tell council to provide agent summary.
        
        Args:
            agent_summary_factory: Factory class for creating AgentSummary instances
        
        Returns:
            AgentSummary with status counts
        """
        return self.agents.get_status_summary(agent_summary_factory)
    
    def to_dict(self) -> dict:
        """Convert council info to dictionary representation.
        
        Used for serialization and API responses.
        
        Returns:
            Dictionary with council information
        """
        return {
            "council_id": self.council_id,
            "role": self.role,
            "emoji": self.emoji,
            "status": self.status,
            "model": self.model,
            "total_agents": self.total_agents,
            "agents": [agent.to_dict() for agent in self.agents.agents],
            "display_name": self.get_display_name(),
        }
    
    @classmethod
    def from_dict(cls, data: dict, agent_info_factory: type[AgentInfo]) -> CouncilInfo:
        """Create CouncilInfo from dictionary.
        
        Factory method for creating CouncilInfo from serialized data.
        
        Args:
            data: Dictionary with council information
            agent_info_factory: Factory class for creating AgentInfo instances
            
        Returns:
            CouncilInfo instance
            
        Raises:
            ValueError: If required fields are missing
        """
        required_fields = {
            "council_id", "role", "emoji", "status", "model", "total_agents"
        }
        missing_fields = required_fields - set(data.keys())
        
        if missing_fields:
            raise ValueError(
                f"Missing required fields: {', '.join(missing_fields)}"
            )
        
        # Convert agents from dict to AgentInfo objects
        agents = []
        if "agents" in data and data["agents"]:
            for agent_data in data["agents"]:
                agents.append(agent_info_factory.from_dict(agent_data))
        
        return cls(
            council_id=data["council_id"],
            role=data["role"],
            emoji=data["emoji"],
            status=data["status"],
            model=data["model"],
            total_agents=data["total_agents"],
            agents=AgentList.create(agents)
        )
    
    @classmethod
    def create_empty_council(
        cls,
        council_id: str,
        role: str,
        model: str = "unknown"
    ) -> CouncilInfo:
        """Create an empty council with no agents.
        
        Factory method for creating empty councils.
        
        Args:
            council_id: Council identifier
            role: Council role
            model: AI model name
            
        Returns:
            CouncilInfo instance with no agents
        """
        role_emojis = {
            "DEV": "🧑‍💻",
            "QA": "🧪",
            "ARCHITECT": "🏗️",
            "DEVOPS": "⚙️",
            "DATA": "📊"
        }
        
        return cls(
            council_id=council_id,
            role=role,
            emoji=role_emojis.get(role, "🤖"),
            status="inactive",
            model=model,
            total_agents=0,
            agents=[]
        )
