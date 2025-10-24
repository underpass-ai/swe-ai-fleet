"""Tests for AgentConfig configuration class."""

import pytest
from core.orchestrator.config_module.agent_configuration import AgentConfig


class TestAgentConfig:
    """Test cases for AgentConfig dataclass."""

    def test_agent_config_creation_with_required_fields(self):
        """Test creating AgentConfig with required fields only."""
        config = AgentConfig(sprint_id="sprint-123", role="developer")
        
        assert config.sprint_id == "sprint-123"
        assert config.role == "developer"
        assert config.workspace == "/workspace"  # default value
        assert config.pick_first_ready is True  # default value

    def test_agent_config_creation_with_all_fields(self):
        """Test creating AgentConfig with all fields specified."""
        config = AgentConfig(
            sprint_id="sprint-456",
            role="architect",
            workspace="/custom/workspace",
            pick_first_ready=False
        )
        
        assert config.sprint_id == "sprint-456"
        assert config.role == "architect"
        assert config.workspace == "/custom/workspace"
        assert config.pick_first_ready is False

    def test_agent_config_immutability(self):
        """Test that AgentConfig is immutable (frozen dataclass)."""
        config = AgentConfig(sprint_id="sprint-789", role="tester")
        
        with pytest.raises(AttributeError):
            config.sprint_id = "new-sprint"
        
        with pytest.raises(AttributeError):
            config.role = "new-role"

    def test_agent_config_equality(self):
        """Test AgentConfig equality comparison."""
        config1 = AgentConfig(sprint_id="sprint-123", role="developer")
        config2 = AgentConfig(sprint_id="sprint-123", role="developer")
        config3 = AgentConfig(sprint_id="sprint-456", role="developer")
        
        assert config1 == config2
        assert config1 != config3

    def test_agent_config_string_representation(self):
        """Test AgentConfig string representation."""
        config = AgentConfig(sprint_id="sprint-123", role="developer")
        str_repr = str(config)
        
        assert "sprint-123" in str_repr
        assert "developer" in str_repr
        assert "AgentConfig" in str_repr
