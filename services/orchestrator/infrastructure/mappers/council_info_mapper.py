"""Mapper for CouncilInfo domain model to/from protobuf."""

from __future__ import annotations

from services.orchestrator.domain.ports.council_query_port import AgentInfo, CouncilInfo
from services.orchestrator.infrastructure.dto import orchestrator_dto


class CouncilInfoMapper:
    """Mapper for CouncilInfo domain model to/from protobuf DTOs.
    
    This mapper handles the conversion between the domain CouncilInfo value object
    and the generated protobuf CouncilInfo message, isolating domain logic from
    infrastructure concerns.
    """
    
    @staticmethod
    def domain_to_proto(council_info: CouncilInfo) -> orchestrator_dto.CouncilInfo:
        """Convert domain CouncilInfo to protobuf CouncilInfo.
        
        Args:
            council_info: Domain CouncilInfo object
            
        Returns:
            Protobuf CouncilInfo message
        """
        # Convert agent infos if present
        agent_infos = []
        if hasattr(council_info, 'agent_infos') and council_info.agent_infos:
            for agent_info in council_info.agent_infos:
                proto_agent = orchestrator_dto.AgentInfo(
                    agent_id=agent_info.agent_id,
                    role=agent_info.role,
                    status=agent_info.status,
                )
                agent_infos.append(proto_agent)
        
        return orchestrator_dto.CouncilInfo(
            council_id=council_info.council_id,
            role=council_info.role,
            num_agents=council_info.num_agents,
            agents=agent_infos,
            status=council_info.status,
            model=council_info.model
        )
    
    @staticmethod
    def domain_list_to_proto_list(
        council_infos: list[CouncilInfo]
    ) -> list[orchestrator_dto.CouncilInfo]:
        """Convert list of domain CouncilInfo to list of protobuf CouncilInfo.
        
        Args:
            council_infos: List of domain CouncilInfo objects
            
        Returns:
            List of protobuf CouncilInfo messages
        """
        return [
            CouncilInfoMapper.domain_to_proto(council_info)
            for council_info in council_infos
        ]
    
    @staticmethod
    def proto_to_domain(proto: orchestrator_dto.CouncilInfo) -> CouncilInfo:
        """Convert protobuf CouncilInfo to domain CouncilInfo.
        
        Args:
            proto: Protobuf CouncilInfo message
            
        Returns:
            Domain CouncilInfo object
        """
        # Create CouncilInfo (without agent_infos in constructor)
        council_info = CouncilInfo(
            council_id=proto.council_id,
            role=proto.role,
            num_agents=proto.num_agents,
            status=proto.status,
            model=proto.model
        )
        
        # Convert and assign agent infos as attribute (always, even if empty)
        agent_infos = []
        if proto.agents:
            for proto_agent in proto.agents:
                agent_info = AgentInfo(
                    agent_id=proto_agent.agent_id,
                    role=proto_agent.role,
                    status=proto_agent.status,
                )
                agent_infos.append(agent_info)
        council_info.agent_infos = agent_infos
        
        return council_info

