"""Port (interface) for council query operations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.orchestrator.domain.entities import CouncilRegistry


class CouncilInfo:
    """Value object representing council information.
    
    Attributes:
        council_id: Unique council identifier
        role: Role name
        num_agents: Number of agents in council
        status: Council status
        model: Model used by agents
    """
    
    def __init__(
        self,
        council_id: str,
        role: str,
        num_agents: int,
        status: str,
        model: str
    ):
        self.council_id = council_id
        self.role = role
        self.num_agents = num_agents
        self.status = status
        self.model = model


class AgentInfo:
    """Value object representing agent information.
    
    Attributes:
        agent_id: Unique agent identifier
        role: Agent role
        status: Agent status
    """
    
    def __init__(self, agent_id: str, role: str, status: str):
        self.agent_id = agent_id
        self.role = role
        self.status = status


class CouncilQueryPort(ABC):
    """Port defining the interface for querying council information.
    
    This port abstracts queries about councils and agents,
    allowing the domain to remain independent of implementation details.
    
    Following Hexagonal Architecture:
    - Domain defines the port (this interface)
    - Infrastructure provides the adapter
    """
    
    @abstractmethod
    def list_councils(
        self,
        council_registry: CouncilRegistry,
        include_agents: bool = False
    ) -> list[CouncilInfo]:
        """List all active councils.
        
        Args:
            council_registry: Council registry to query
            include_agents: Whether to include agent details
            
        Returns:
            List of CouncilInfo objects
        """
        pass
    
    @abstractmethod
    def get_council_info(
        self,
        council_registry: CouncilRegistry,
        role: str,
        include_agents: bool = False
    ) -> CouncilInfo:
        """Get information about a specific council.
        
        Args:
            council_registry: Council registry to query
            role: Role name
            include_agents: Whether to include agent details
            
        Returns:
            CouncilInfo object
            
        Raises:
            ValueError: If council not found
        """
        pass

