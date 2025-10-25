"""Mapper for converting protobuf Agent to domain AgentInfo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from services.monitoring.domain.entities.orchestrator.agent_info import AgentInfo

if TYPE_CHECKING:
    # Import protobuf types only for type checking
    pass


class AgentInfoMapper:
    """Mapper for converting protobuf Agent to domain AgentInfo.
    
    This mapper follows the Mapper pattern from Hexagonal Architecture,
    translating between infrastructure (protobuf) and domain (entities)
    layers. It encapsulates the conversion logic and provides a clean
    interface for data transformation.
    """
    
    @staticmethod
    def proto_to_domain(proto_agent) -> AgentInfo:
        """Convert protobuf Agent to domain AgentInfo.
        
        Args:
            proto_agent: Protobuf Agent message
            
        Returns:
            AgentInfo domain entity
            
        Raises:
            ValueError: If protobuf data is invalid or missing required fields
        """
        if not proto_agent:
            raise ValueError("Proto agent cannot be None")
        
        # Extract required fields with validation
        agent_id = proto_agent.agent_id
        if not agent_id or not agent_id.strip():
            raise ValueError("Agent ID cannot be empty")
        
        role = proto_agent.role
        if not role or not role.strip():
            raise ValueError("Agent role cannot be empty")
        
        # Use provided status or default to "idle"
        status = proto_agent.status if proto_agent.status else "idle"
        
        return AgentInfo(
            agent_id=agent_id.strip(),
            role=role.strip(),
            status=status.strip()
        )
    
    @staticmethod
    def domain_to_proto(agent_info: AgentInfo) -> dict:
        """Convert domain AgentInfo to protobuf-compatible dictionary.
        
        This method is provided for completeness and future use cases
        where we might need to send agent information back to the
        orchestrator service.
        
        Args:
            agent_info: AgentInfo domain entity
            
        Returns:
            Dictionary compatible with protobuf Agent message
        """
        return {
            "agent_id": agent_info.agent_id,
            "role": agent_info.role,
            "status": agent_info.status
        }
    
    @staticmethod
    def create_fallback_agent(role: str, agent_index: int) -> AgentInfo:
        """Create a fallback agent when protobuf data is incomplete.
        
        This method creates a default agent with a generated ID when
        the protobuf response doesn't include agent details.
        
        Args:
            role: Agent role (e.g., "DEV", "QA")
            agent_index: Index for generating unique agent ID
            
        Returns:
            AgentInfo with fallback data
        """
        return AgentInfo(
            agent_id=f"agent-{role.lower()}-{agent_index+1:03d}",
            role=role,
            status="idle"
        )
