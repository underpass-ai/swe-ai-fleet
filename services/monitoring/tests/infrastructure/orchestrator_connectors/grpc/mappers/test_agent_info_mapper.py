"""Tests for AgentInfoMapper."""

from unittest.mock import MagicMock

import pytest
from services.monitoring.domain.entities.orchestrator.agent_info import AgentInfo
from services.monitoring.infrastructure.orchestrator_connectors.grpc.mappers.agent_info_mapper import (
    AgentInfoMapper,
)


class TestAgentInfoMapper:
    """Test cases for AgentInfoMapper."""
    
    def test_proto_to_domain_success(self):
        """Test successful conversion from protobuf to domain."""
        # Create mock protobuf agent
        mock_proto_agent = MagicMock()
        mock_proto_agent.agent_id = "agent-dev-001"
        mock_proto_agent.role = "DEV"
        mock_proto_agent.status = "ready"
        
        result = AgentInfoMapper.proto_to_domain(mock_proto_agent)
        
        assert isinstance(result, AgentInfo)
        assert result.agent_id == "agent-dev-001"
        assert result.role == "DEV"
        assert result.status == "ready"
    
    def test_proto_to_domain_with_none_status(self):
        """Test conversion with None status (should default to 'idle')."""
        mock_proto_agent = MagicMock()
        mock_proto_agent.agent_id = "agent-dev-001"
        mock_proto_agent.role = "DEV"
        mock_proto_agent.status = None
        
        result = AgentInfoMapper.proto_to_domain(mock_proto_agent)
        
        assert result.status == "idle"
    
    def test_proto_to_domain_with_empty_status(self):
        """Test conversion with empty status (should default to 'idle')."""
        mock_proto_agent = MagicMock()
        mock_proto_agent.agent_id = "agent-dev-001"
        mock_proto_agent.role = "DEV"
        mock_proto_agent.status = ""
        
        result = AgentInfoMapper.proto_to_domain(mock_proto_agent)
        
        assert result.status == "idle"
    
    def test_proto_to_domain_strips_whitespace(self):
        """Test that whitespace is stripped from fields."""
        mock_proto_agent = MagicMock()
        mock_proto_agent.agent_id = "  agent-dev-001  "
        mock_proto_agent.role = "  DEV  "
        mock_proto_agent.status = "  ready  "
        
        result = AgentInfoMapper.proto_to_domain(mock_proto_agent)
        
        assert result.agent_id == "agent-dev-001"
        assert result.role == "DEV"
        assert result.status == "ready"
    
    def test_proto_to_domain_none_proto_raises_error(self):
        """Test that None proto agent raises ValueError."""
        with pytest.raises(ValueError, match="Proto agent cannot be None"):
            AgentInfoMapper.proto_to_domain(None)
    
    def test_proto_to_domain_empty_agent_id_raises_error(self):
        """Test that empty agent ID raises ValueError."""
        mock_proto_agent = MagicMock()
        mock_proto_agent.agent_id = ""
        mock_proto_agent.role = "DEV"
        mock_proto_agent.status = "ready"
        
        with pytest.raises(ValueError, match="Agent ID cannot be empty"):
            AgentInfoMapper.proto_to_domain(mock_proto_agent)
    
    def test_proto_to_domain_whitespace_agent_id_raises_error(self):
        """Test that whitespace-only agent ID raises ValueError."""
        mock_proto_agent = MagicMock()
        mock_proto_agent.agent_id = "   "
        mock_proto_agent.role = "DEV"
        mock_proto_agent.status = "ready"
        
        with pytest.raises(ValueError, match="Agent ID cannot be empty"):
            AgentInfoMapper.proto_to_domain(mock_proto_agent)
    
    def test_proto_to_domain_empty_role_raises_error(self):
        """Test that empty role raises ValueError."""
        mock_proto_agent = MagicMock()
        mock_proto_agent.agent_id = "agent-dev-001"
        mock_proto_agent.role = ""
        mock_proto_agent.status = "ready"
        
        with pytest.raises(ValueError, match="Agent role cannot be empty"):
            AgentInfoMapper.proto_to_domain(mock_proto_agent)
    
    def test_proto_to_domain_whitespace_role_raises_error(self):
        """Test that whitespace-only role raises ValueError."""
        mock_proto_agent = MagicMock()
        mock_proto_agent.agent_id = "agent-dev-001"
        mock_proto_agent.role = "   "
        mock_proto_agent.status = "ready"
        
        with pytest.raises(ValueError, match="Agent role cannot be empty"):
            AgentInfoMapper.proto_to_domain(mock_proto_agent)
    
    def test_domain_to_proto(self):
        """Test conversion from domain to protobuf-compatible dictionary."""
        agent_info = AgentInfo(
            agent_id="agent-dev-001",
            role="DEV",
            status="ready"
        )
        
        result = AgentInfoMapper.domain_to_proto(agent_info)
        
        expected = {
            "agent_id": "agent-dev-001",
            "role": "DEV",
            "status": "ready"
        }
        assert result == expected
    
    def test_create_fallback_agent(self):
        """Test creation of fallback agent."""
        result = AgentInfoMapper.create_fallback_agent("DEV", 0)
        
        assert isinstance(result, AgentInfo)
        assert result.agent_id == "agent-dev-001"
        assert result.role == "DEV"
        assert result.status == "idle"
    
    def test_create_fallback_agent_with_index(self):
        """Test creation of fallback agent with different index."""
        result = AgentInfoMapper.create_fallback_agent("QA", 2)
        
        assert isinstance(result, AgentInfo)
        assert result.agent_id == "agent-qa-003"
        assert result.role == "QA"
        assert result.status == "idle"
    
    def test_create_fallback_agent_lowercase_role(self):
        """Test creation of fallback agent with lowercase role."""
        result = AgentInfoMapper.create_fallback_agent("ARCHITECT", 1)
        
        assert isinstance(result, AgentInfo)
        assert result.agent_id == "agent-architect-002"
        assert result.role == "ARCHITECT"
        assert result.status == "idle"
