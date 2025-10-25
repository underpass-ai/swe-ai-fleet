"""Orchestrator information aggregate root."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .agent_info import AgentInfo
    from .council_info import CouncilInfo
    from .orchestrator_connection_status import OrchestratorConnectionStatus


@dataclass(frozen=True)
class OrchestratorInfo:
    """Aggregate root representing complete orchestrator information.
    
    This aggregate root encapsulates all information about the orchestrator
    service, including connection status, councils, and agents. It follows
    the Aggregate Root pattern from DDD and serves as the main entry point
    for orchestrator-related operations.
    
    Attributes:
        connection_status: Current connection status and metrics
        councils: List of CouncilInfo objects representing all councils
    """
    
    connection_status: OrchestratorConnectionStatus
    councils: list[CouncilInfo] = field(default_factory=list)
    
    def __init__(
        self,
        connection_status: OrchestratorConnectionStatus,
        councils: list[CouncilInfo] | None = None
    ):
        """Initialize OrchestratorInfo with validation.
        
        Args:
            connection_status: Current connection status and metrics.
            councils: List of CouncilInfo objects representing all councils.
            
        Raises:
            ValueError: If data is inconsistent or invalid.
        """
        councils = councils or []
        
        # Validate councils consistency with connection status
        if connection_status.is_connected():
            expected_councils = connection_status.total_councils
            actual_councils = len(councils)
            
            if actual_councils != expected_councils:
                raise ValueError(
                    f"Councils count mismatch: expected {expected_councils} "
                    f"but got {actual_councils}"
                )
            
            expected_agents = connection_status.total_agents
            actual_agents = sum(council.total_agents for council in councils)
            
            if actual_agents != expected_agents:
                raise ValueError(
                    f"Agents count mismatch: expected {expected_agents} "
                    f"but got {actual_agents}"
                )
        
        # Set validated values
        object.__setattr__(self, 'connection_status', connection_status)
        object.__setattr__(self, 'councils', councils)
    
    @property
    def total_councils(self) -> int:
        """Get total number of councils.
        
        Tell, Don't Ask: Tell aggregate to provide total councils count.
        
        Returns:
            Total number of councils
        """
        return len(self.councils)
    
    @property
    def total_agents(self) -> int:
        """Get total number of agents across all councils.
        
        Tell, Don't Ask: Tell aggregate to provide total agents count.
        
        Returns:
            Total number of agents
        """
        return sum(council.total_agents for council in self.councils)
    
    def is_connected(self) -> bool:
        """Check if orchestrator is connected.
        
        Tell, Don't Ask: Tell aggregate to check if connected.
        
        Returns:
            True if connected, False otherwise
        """
        return self.connection_status.is_connected()
    
    def is_healthy(self) -> bool:
        """Check if orchestrator is healthy.
        
        Tell, Don't Ask: Tell aggregate to check if healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        return self.connection_status.is_healthy()
    
    def has_councils(self) -> bool:
        """Check if orchestrator has any councils.
        
        Tell, Don't Ask: Tell aggregate to check if has councils.
        
        Returns:
            True if has councils, False otherwise
        """
        return len(self.councils) > 0
    
    def has_agents(self) -> bool:
        """Check if orchestrator has any agents.
        
        Tell, Don't Ask: Tell aggregate to check if has agents.
        
        Returns:
            True if has agents, False otherwise
        """
        return self.total_agents > 0
    
    def get_council_by_role(self, role: str) -> CouncilInfo | None:
        """Get council by role.
        
        Tell, Don't Ask: Tell aggregate to get council by role.
        
        Args:
            role: Council role (e.g., "DEV", "QA", "ARCHITECT")
            
        Returns:
            CouncilInfo if found, None otherwise
        """
        for council in self.councils:
            if council.role == role:
                return council
        return None
    
    def has_council(self, role: str) -> bool:
        """Check if orchestrator has council with given role.
        
        Tell, Don't Ask: Tell aggregate to check if has council.
        
        Args:
            role: Council role
            
        Returns:
            True if council exists, False otherwise
        """
        return self.get_council_by_role(role) is not None
    
    def get_councils_by_status(self, status: str) -> list[CouncilInfo]:
        """Get councils by status.
        
        Tell, Don't Ask: Tell aggregate to provide councils by status.
        
        Args:
            status: Council status (e.g., "active", "idle", "inactive")
            
        Returns:
            List of councils with the specified status
        """
        return [council for council in self.councils if council.status == status]
    
    def get_active_councils(self) -> list[CouncilInfo]:
        """Get all active councils.
        
        Tell, Don't Ask: Tell aggregate to provide active councils.
        
        Returns:
            List of active councils
        """
        return [council for council in self.councils if council.is_active()]
    
    def get_idle_councils(self) -> list[CouncilInfo]:
        """Get all idle councils.
        
        Tell, Don't Ask: Tell aggregate to provide idle councils.
        
        Returns:
            List of idle councils
        """
        return [council for council in self.councils if council.is_idle()]
    
    def get_offline_councils(self) -> list[CouncilInfo]:
        """Get all offline councils.
        
        Tell, Don't Ask: Tell aggregate to provide offline councils.
        
        Returns:
            List of offline councils
        """
        return [council for council in self.councils if council.is_offline()]
    
    def get_all_agents(self) -> list[AgentInfo]:
        """Get all agents from all councils.
        
        Tell, Don't Ask: Tell aggregate to provide all agents.
        
        Returns:
            List of all agents across all councils
        """
        agents = []
        for council in self.councils:
            agents.extend(council.agents.to_list())
        return agents
    
    def get_agents_by_role(self, role: str) -> list[AgentInfo]:
        """Get agents by role.
        
        Tell, Don't Ask: Tell aggregate to provide agents by role.
        
        Args:
            role: Agent role (e.g., "DEV", "QA", "ARCHITECT")
            
        Returns:
            List of agents with the specified role
        """
        agents = []
        for council in self.councils:
            if council.role == role:
                agents.extend(council.agents.to_list())
        return agents
    
    def get_agents_by_status(self, status: str) -> list[AgentInfo]:
        """Get agents by status.
        
        Tell, Don't Ask: Tell aggregate to provide agents by status.
        
        Args:
            status: Agent status (e.g., "ready", "idle", "busy")
            
        Returns:
            List of agents with the specified status
        """
        agents = []
        for council in self.councils:
            for agent in council.agents.agents:
                if agent.status == status:
                    agents.append(agent)
        return agents
    
    def get_ready_agents(self) -> list[AgentInfo]:
        """Get all ready agents.
        
        Tell, Don't Ask: Tell aggregate to provide ready agents.
        
        Returns:
            List of ready agents
        """
        agents = []
        for council in self.councils:
            agents.extend(council.get_ready_agents())
        return agents
    
    def get_busy_agents(self) -> list[AgentInfo]:
        """Get all busy agents.
        
        Tell, Don't Ask: Tell aggregate to provide busy agents.
        
        Returns:
            List of busy agents
        """
        agents = []
        for council in self.councils:
            agents.extend(council.get_busy_agents())
        return agents
    
    def get_offline_agents(self) -> list[AgentInfo]:
        """Get all offline agents.
        
        Tell, Don't Ask: Tell aggregate to provide offline agents.
        
        Returns:
            List of offline agents
        """
        agents = []
        for council in self.councils:
            agents.extend(council.get_offline_agents())
        return agents
    
    def get_agent_by_id(self, agent_id: str) -> AgentInfo | None:
        """Get agent by ID across all councils.
        
        Tell, Don't Ask: Tell aggregate to get agent by ID.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            AgentInfo if found, None otherwise
        """
        for council in self.councils:
            agent = council.get_agent_by_id(agent_id)
            if agent is not None:
                return agent
        return None
    
    def has_agent(self, agent_id: str) -> bool:
        """Check if orchestrator has agent with given ID.
        
        Tell, Don't Ask: Tell aggregate to check if has agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            True if agent exists, False otherwise
        """
        return self.get_agent_by_id(agent_id) is not None
    
    def get_council_summary(self) -> dict[str, int]:
        """Get summary of councils by status.
        
        Tell, Don't Ask: Tell aggregate to provide council summary.
        
        Returns:
            Dictionary with status counts
        """
        summary = {}
        for council in self.councils:
            status = council.status
            summary[status] = summary.get(status, 0) + 1
        return summary
    
    def get_agent_summary(self) -> dict[str, int]:
        """Get summary of agents by status.
        
        Tell, Don't Ask: Tell aggregate to provide agent summary.
        
        Returns:
            Dictionary with status counts
        """
        summary = {}
        for council in self.councils:
            for agent in council.agents.agents:
                status = agent.status
                summary[status] = summary.get(status, 0) + 1
        return summary
    
    def get_role_summary(self) -> dict[str, int]:
        """Get summary of councils by role.
        
        Tell, Don't Ask: Tell aggregate to provide role summary.
        
        Returns:
            Dictionary with role counts
        """
        summary = {}
        for council in self.councils:
            role = council.role
            summary[role] = summary.get(role, 0) + 1
        return summary
    
    def get_health_summary(self) -> dict[str, any]:
        """Get comprehensive health summary.
        
        Tell, Don't Ask: Tell aggregate to provide health summary.
        
        Returns:
            Dictionary with comprehensive health information
        """
        return {
            "is_connected": self.is_connected(),
            "is_healthy": self.is_healthy(),
            "connection_status": self.connection_status.get_status_summary(),
            "total_councils": self.total_councils,
            "total_agents": self.total_agents,
            "council_summary": self.get_council_summary(),
            "agent_summary": self.get_agent_summary(),
            "role_summary": self.get_role_summary(),
            "active_councils": len(self.get_active_councils()),
            "ready_agents": len(self.get_ready_agents()),
            "busy_agents": len(self.get_busy_agents()),
            "offline_agents": len(self.get_offline_agents())
        }
    
    def to_dict(self) -> dict:
        """Convert orchestrator info to dictionary representation.
        
        Used for serialization and API responses.
        
        Returns:
            Dictionary with orchestrator information
        """
        return {
            "connection_status": self.connection_status.to_dict(),
            "councils": [council.to_dict() for council in self.councils],
            "total_councils": self.total_councils,
            "total_agents": self.total_agents,
            "is_connected": self.is_connected(),
            "is_healthy": self.is_healthy(),
            "health_summary": self.get_health_summary()
        }
    
    @classmethod
    def from_dict(cls, data: dict, council_info_factory: type[CouncilInfo], 
                  orchestrator_connection_status_factory: type[OrchestratorConnectionStatus],
                  agent_info_factory: type[AgentInfo]) -> OrchestratorInfo:
        """Create OrchestratorInfo from dictionary.
        
        Factory method for creating OrchestratorInfo from serialized data.
        
        Args:
            data: Dictionary with orchestrator information
            council_info_factory: Factory class for creating CouncilInfo instances
            orchestrator_connection_status_factory: Factory class for creating OrchestratorConnectionStatus instances
            
        Returns:
            OrchestratorInfo instance
            
        Raises:
            ValueError: If required fields are missing
        """
        required_fields = {"connection_status", "councils"}
        missing_fields = required_fields - set(data.keys())
        
        if missing_fields:
            raise ValueError(
                f"Missing required fields: {', '.join(missing_fields)}"
            )
        
        # Convert connection status
        connection_status = orchestrator_connection_status_factory.from_dict(data["connection_status"])
        
        # Convert councils
        councils = []
        for council_data in data["councils"]:
            councils.append(council_info_factory.from_dict(council_data, agent_info_factory))
        
        return cls(
            connection_status=connection_status,
            councils=councils
        )
    
    @classmethod
    def create_empty_orchestrator(cls) -> OrchestratorInfo:
        """Create empty orchestrator (disconnected with no councils).
        
        Factory method for creating empty orchestrator.
        
        Returns:
            OrchestratorInfo instance for empty state
        """
        from .orchestrator_connection_status import OrchestratorConnectionStatus
        
        return cls(
            connection_status=OrchestratorConnectionStatus.create_empty_status(),
            councils=[]
        )
    
    @classmethod
    def create_connected_orchestrator(
        cls,
        councils: list[CouncilInfo]
    ) -> OrchestratorInfo:
        """Create connected orchestrator with councils.
        
        Factory method for creating connected orchestrator.
        
        Args:
            councils: List of CouncilInfo objects
            
        Returns:
            OrchestratorInfo instance for connected state
        """
        from .orchestrator_connection_status import OrchestratorConnectionStatus
        
        total_councils = len(councils)
        total_agents = sum(council.total_agents for council in councils)
        
        connection_status = OrchestratorConnectionStatus.create_connected_status(
            total_councils=total_councils,
            total_agents=total_agents
        )
        
        return cls(
            connection_status=connection_status,
            councils=councils
        )
    
    @classmethod
    def create_disconnected_orchestrator(
        cls,
        error: str,
        councils: list[CouncilInfo] | None = None
    ) -> OrchestratorInfo:
        """Create disconnected orchestrator.
        
        Factory method for creating disconnected orchestrator.
        
        Args:
            error: Error message
            councils: Optional list of CouncilInfo objects
            
        Returns:
            OrchestratorInfo instance for disconnected state
        """
        from .orchestrator_connection_status import OrchestratorConnectionStatus
        
        councils = councils or []
        total_councils = len(councils)
        total_agents = sum(council.total_agents for council in councils)
        
        connection_status = OrchestratorConnectionStatus.create_disconnected_status(
            error=error,
            total_councils=total_councils,
            total_agents=total_agents
        )
        
        return cls(
            connection_status=connection_status,
            councils=councils
        )
