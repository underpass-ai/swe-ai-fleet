"""Mapper for converting protobuf Council to domain CouncilInfo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from services.monitoring.domain.entities.orchestrator.council_info import CouncilInfo

from .agent_info_mapper import AgentInfoMapper

if TYPE_CHECKING:
    # Import protobuf types only for type checking
    pass


class CouncilInfoMapper:
    """Mapper for converting protobuf Council to domain CouncilInfo.
    
    This mapper follows the Mapper pattern from Hexagonal Architecture,
    translating between infrastructure (protobuf) and domain (entities)
    layers. It handles the conversion of council data and its associated
    agents using the AgentInfoMapper.
    """
    
    # Role to emoji mapping
    ROLE_EMOJIS = {
        "DEV": "🧑‍💻",
        "QA": "🧪",
        "ARCHITECT": "🏗️",
        "DEVOPS": "⚙️",
        "DATA": "📊"
    }
    
    @staticmethod
    def proto_to_domain(proto_council) -> CouncilInfo:
        """Convert protobuf Council to domain CouncilInfo.
        
        Args:
            proto_council: Protobuf Council message
            
        Returns:
            CouncilInfo domain entity
            
        Raises:
            ValueError: If protobuf data is invalid or missing required fields
        """
        if not proto_council:
            raise ValueError("Proto council cannot be None")
        
        # Extract and validate basic fields
        role = CouncilInfoMapper._extract_and_validate_role(proto_council)
        emoji = CouncilInfoMapper.ROLE_EMOJIS.get(role, "🤖")
        status = CouncilInfoMapper._extract_status(proto_council)
        model = CouncilInfoMapper._extract_model(proto_council)
        total_agents = CouncilInfoMapper._extract_total_agents(proto_council)
        
        # Convert agents
        agents = CouncilInfoMapper._convert_agents(proto_council, role, total_agents)
        
        # Generate council ID
        council_id = f"council-{role.lower()}-001"
        
        return CouncilInfo(
            council_id=council_id,
            role=role,
            emoji=emoji,
            status=status,
            model=model,
            total_agents=total_agents,
            agents=agents
        )
    
    @staticmethod
    def _extract_and_validate_role(proto_council) -> str:
        """Extract and validate council role."""
        role = proto_council.role
        if not role or not role.strip():
            raise ValueError("Council role cannot be empty")
        return role.strip()
    
    @staticmethod
    def _extract_status(proto_council) -> str:
        """Extract council status."""
        status = proto_council.status if proto_council.status else "idle"
        return "active" if status == "active" else "idle"
    
    @staticmethod
    def _extract_model(proto_council) -> str:
        """Extract council model."""
        return proto_council.model if proto_council.model else "unknown"
    
    @staticmethod
    def _extract_total_agents(proto_council) -> int:
        """Extract total agents count."""
        return proto_council.num_agents if hasattr(proto_council, 'num_agents') else 0
    
    @staticmethod
    def _convert_agents(proto_council, role: str, total_agents: int) -> list:
        """Convert protobuf agents to domain agents."""
        agents = []
        if proto_council.agents:
            # Use provided agents
            for proto_agent in proto_council.agents:
                try:
                    agent = AgentInfoMapper.proto_to_domain(proto_agent)
                    agents.append(agent)
                except ValueError as e:
                    # Log warning but continue with other agents
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to convert agent: {e}")
        else:
            # Create fallback agents if none provided
            for i in range(total_agents):
                agent = AgentInfoMapper.create_fallback_agent(role, i)
                agents.append(agent)
        return agents
    
    @staticmethod
    def domain_to_proto(council_info: CouncilInfo) -> dict:
        """Convert domain CouncilInfo to protobuf-compatible dictionary.
        
        This method is provided for completeness and future use cases
        where we might need to send council information back to the
        orchestrator service.
        
        Args:
            council_info: CouncilInfo domain entity
            
        Returns:
            Dictionary compatible with protobuf Council message
        """
        return {
            "council_id": council_info.council_id,
            "role": council_info.role,
            "emoji": council_info.emoji,
            "status": council_info.status,
            "model": council_info.model,
            "total_agents": council_info.total_agents,
            "agents": [
                AgentInfoMapper.domain_to_proto(agent) 
                for agent in council_info.agents
            ]
        }
    
    @staticmethod
    def create_empty_council(
        role: str,
        model: str = "unknown"
    ) -> CouncilInfo:
        """Create an empty council with no agents.
        
        This method creates a council in idle state with no agents,
        useful for representing councils that exist but have no
        active agents.
        
        Args:
            role: Council role (e.g., "DEV", "QA")
            model: Model name (defaults to "unknown")
            
        Returns:
            CouncilInfo with empty agents list
        """
        emoji = CouncilInfoMapper.ROLE_EMOJIS.get(role, "🤖")
        council_id = f"council-{role.lower()}-001"
        
        return CouncilInfo(
            council_id=council_id,
            role=role,
            emoji=emoji,
            status="idle",
            model=model,
            total_agents=0,
            agents=[]
        )
