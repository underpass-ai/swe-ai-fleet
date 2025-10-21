"""Tests for CouncilInfoMapper."""

from services.orchestrator.domain.ports.council_query_port import AgentInfo, CouncilInfo
from services.orchestrator.infrastructure.dto import orchestrator_dto
from services.orchestrator.infrastructure.mappers import CouncilInfoMapper


class TestCouncilInfoMapper:
    """Test suite for CouncilInfoMapper."""
    
    def test_domain_to_proto_without_agents(self):
        """Test converting CouncilInfo to protobuf without agents."""
        council_info = CouncilInfo(
            council_id="council-coder",
            role="Coder",
            num_agents=3,
            status="active",
            model="gpt-4"
        )
        council_info.agent_infos = []  # Assigned as attribute
        
        proto = CouncilInfoMapper.domain_to_proto(council_info)
        
        assert proto.council_id == "council-coder"
        assert proto.role == "Coder"
        assert proto.num_agents == 3
        assert len(proto.agents) == 0
        assert proto.status == "active"
        assert proto.model == "gpt-4"
    
    def test_domain_to_proto_with_agents(self):
        """Test converting CouncilInfo to protobuf with agents."""
        agent_infos = [
            AgentInfo("agent-001", "Coder", "active"),
            AgentInfo("agent-002", "Coder", "active")
        ]
        council_info = CouncilInfo(
            council_id="council-coder",
            role="Coder",
            num_agents=2,
            status="active",
            model="gpt-4"
        )
        council_info.agent_infos = agent_infos  # Assigned as attribute
        
        proto = CouncilInfoMapper.domain_to_proto(council_info)
        
        assert len(proto.agents) == 2
        assert proto.agents[0].agent_id == "agent-001"
        assert proto.agents[1].agent_id == "agent-002"
    
    def test_domain_list_to_proto_list(self):
        """Test converting list of CouncilInfo to protobuf list."""
        c1 = CouncilInfo("c1", "Coder", 3, "active", "gpt-4")
        c1.agent_infos = []
        c2 = CouncilInfo("c2", "Reviewer", 2, "active", "gpt-3.5")
        c2.agent_infos = []
        council_infos = [c1, c2]
        
        proto_list = CouncilInfoMapper.domain_list_to_proto_list(council_infos)
        
        assert len(proto_list) == 2
        assert proto_list[0].role == "Coder"
        assert proto_list[1].role == "Reviewer"
    
    def test_proto_to_domain_without_agents(self):
        """Test converting protobuf to CouncilInfo without agents."""
        proto = orchestrator_dto.CouncilInfo(
            council_id="council-coder",
            role="Coder",
            num_agents=3,
            agents=[],
            status="active",
            model="gpt-4"
        )
        
        council_info = CouncilInfoMapper.proto_to_domain(proto)
        
        assert council_info.council_id == "council-coder"
        assert council_info.role == "Coder"
        assert council_info.num_agents == 3
        assert len(council_info.agent_infos) == 0
    
    def test_proto_to_domain_with_agents(self):
        """Test converting protobuf to CouncilInfo with agents."""
        proto = orchestrator_dto.CouncilInfo(
            council_id="council-coder",
            role="Coder",
            num_agents=2,
            agents=[
                orchestrator_dto.AgentInfo(
                    agent_id="agent-001",
                    role="Coder",
                    status="active"
                )
            ],
            status="active",
            model="gpt-4"
        )
        
        council_info = CouncilInfoMapper.proto_to_domain(proto)
        
        assert len(council_info.agent_infos) == 1
        assert council_info.agent_infos[0].agent_id == "agent-001"

