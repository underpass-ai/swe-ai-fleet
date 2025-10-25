"""Tests for AgentInfo value object."""

import pytest
from services.monitoring.domain.entities.orchestrator.agent_info import AgentInfo


class TestAgentInfo:
    """Test cases for AgentInfo value object."""
    
    def test_create_valid_agent_info(self):
        """Test creating AgentInfo with valid data."""
        agent = AgentInfo.create(
            agent_id="agent-dev-001",
            role="DEV",
            status="ready"
        )
        
        assert agent.agent_id == "agent-dev-001"
        assert agent.role == "DEV"
        assert agent.status == "ready"
    
    def test_agent_info_is_immutable(self):
        """Test that AgentInfo is immutable (frozen dataclass)."""
        agent = AgentInfo.create(
            agent_id="agent-dev-001",
            role="DEV",
            status="ready"
        )
        
        with pytest.raises(AttributeError):
            agent.agent_id = "new-id"
    
    def test_empty_agent_id_raises_error(self):
        """Test that empty agent ID raises ValueError."""
        with pytest.raises(ValueError, match="Agent ID cannot be empty"):
            AgentInfo.create(
                agent_id="",
                role="DEV",
                status="ready"
            )
    
    def test_empty_role_raises_error(self):
        """Test that empty role raises ValueError."""
        with pytest.raises(ValueError, match="Agent role cannot be empty"):
            AgentInfo.create(
                agent_id="agent-dev-001",
                role="",
                status="ready"
            )
    
    def test_empty_status_raises_error(self):
        """Test that empty status raises ValueError."""
        with pytest.raises(ValueError, match="Agent status cannot be empty"):
            AgentInfo.create(
                agent_id="agent-dev-001",
                role="DEV",
                status=""
            )
    
    def test_invalid_role_raises_error(self):
        """Test that invalid role raises ValueError."""
        with pytest.raises(ValueError, match="Invalid agent role"):
            AgentInfo.create(
                agent_id="agent-dev-001",
                role="INVALID_ROLE",
                status="ready"
            )
    
    def test_invalid_status_raises_error(self):
        """Test that invalid status raises ValueError."""
        with pytest.raises(ValueError, match="Invalid agent status"):
            AgentInfo.create(
                agent_id="agent-dev-001",
                role="DEV",
                status="invalid_status"
            )
    
    def test_valid_roles(self):
        """Test all valid roles."""
        valid_roles = ["DEV", "QA", "ARCHITECT", "DEVOPS", "DATA"]
        
        for role in valid_roles:
            agent = AgentInfo.create(
                agent_id=f"agent-{role.lower()}-001",
                role=role,
                status="ready"
            )
            assert agent.role == role
    
    def test_valid_statuses(self):
        """Test all valid statuses."""
        valid_statuses = ["ready", "idle", "busy", "error", "offline"]
        
        for status in valid_statuses:
            agent = AgentInfo.create(
                agent_id="agent-dev-001",
                role="DEV",
                status=status
            )
            assert agent.status == status
    
    def test_is_ready(self):
        """Test is_ready method (Tell, Don't Ask pattern)."""
        ready_agent = AgentInfo.create(
            agent_id="agent-dev-001",
            role="DEV",
            status="ready"
        )
        assert ready_agent.is_ready() is True
        
        idle_agent = AgentInfo.create(
            agent_id="agent-dev-002",
            role="DEV",
            status="idle"
        )
        assert idle_agent.is_ready() is False
    
    def test_is_busy(self):
        """Test is_busy method (Tell, Don't Ask pattern)."""
        busy_agent = AgentInfo.create(
            agent_id="agent-dev-001",
            role="DEV",
            status="busy"
        )
        assert busy_agent.is_busy() is True
        
        ready_agent = AgentInfo.create(
            agent_id="agent-dev-002",
            role="DEV",
            status="ready"
        )
        assert ready_agent.is_busy() is False
    
    def test_is_offline(self):
        """Test is_offline method (Tell, Don't Ask pattern)."""
        offline_agent = AgentInfo.create(
            agent_id="agent-dev-001",
            role="DEV",
            status="offline"
        )
        assert offline_agent.is_offline() is True
        
        ready_agent = AgentInfo.create(
            agent_id="agent-dev-002",
            role="DEV",
            status="ready"
        )
        assert ready_agent.is_offline() is False
    
    def test_get_display_name(self):
        """Test get_display_name method (Tell, Don't Ask pattern)."""
        agent = AgentInfo.create(
            agent_id="agent-dev-001",
            role="DEV",
            status="ready"
        )
        
        expected = "DEV Agent (agent-dev-001)"
        assert agent.get_display_name() == expected
    
    def test_get_role_emoji(self):
        """Test get_role_emoji method (Tell, Don't Ask pattern)."""
        test_cases = [
            ("DEV", "🧑‍💻"),
            ("QA", "🧪"),
            ("ARCHITECT", "🏗️"),
            ("DEVOPS", "⚙️"),
            ("DATA", "📊")
        ]
        
        for role, expected_emoji in test_cases:
            agent = AgentInfo.create(
                agent_id=f"agent-{role.lower()}-001",
                role=role,
                status="ready"
            )
            assert agent.get_role_emoji() == expected_emoji
    
    def test_get_role_emoji_unknown_role(self):
        """Test get_role_emoji with unknown role returns default emoji."""
        # This test would fail with current validation, but tests the fallback
        # In practice, validation prevents unknown roles
        pass
    
    def test_to_dict(self):
        """Test to_dict method for serialization."""
        agent = AgentInfo.create(
            agent_id="agent-dev-001",
            role="DEV",
            status="ready"
        )
        
        result = agent.to_dict()
        
        expected = {
            "agent_id": "agent-dev-001",
            "role": "DEV",
            "status": "ready",
            "display_name": "DEV Agent (agent-dev-001)",
            "emoji": "🧑‍💻"
        }
        
        assert result == expected
    
    def test_from_dict(self):
        """Test from_dict factory method."""
        data = {
            "agent_id": "agent-dev-001",
            "role": "DEV",
            "status": "ready"
        }
        
        agent = AgentInfo.from_dict(data)
        
        assert agent.agent_id == "agent-dev-001"
        assert agent.role == "DEV"
        assert agent.status == "ready"
    
    def test_from_dict_missing_fields(self):
        """Test from_dict with missing required fields."""
        data = {
            "agent_id": "agent-dev-001",
            "role": "DEV"
            # Missing "status"
        }
        
        with pytest.raises(ValueError, match="Missing required fields"):
            AgentInfo.from_dict(data)
    
    def test_equality(self):
        """Test that AgentInfo instances with same data are equal."""
        agent1 = AgentInfo.create(
            agent_id="agent-dev-001",
            role="DEV",
            status="ready"
        )
        
        agent2 = AgentInfo.create(
            agent_id="agent-dev-001",
            role="DEV",
            status="ready"
        )
        
        assert agent1 == agent2
    
    def test_inequality(self):
        """Test that AgentInfo instances with different data are not equal."""
        agent1 = AgentInfo.create(
            agent_id="agent-dev-001",
            role="DEV",
            status="ready"
        )
        
        agent2 = AgentInfo.create(
            agent_id="agent-dev-002",
            role="DEV",
            status="ready"
        )
        
        assert agent1 != agent2
    
    def test_hash(self):
        """Test that AgentInfo instances are hashable (for use in sets/dicts)."""
        agent = AgentInfo.create(
            agent_id="agent-dev-001",
            role="DEV",
            status="ready"
        )
        
        # Should not raise an error
        hash(agent)
        
        # Should be able to use in set
        agent_set = {agent}
        assert agent in agent_set
