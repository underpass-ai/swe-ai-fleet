"""Tests for AgentConfig value object."""

from pathlib import Path

import pytest
from core.ray_jobs.domain import AgentConfig, AgentRole


class TestAgentConfig:
    """Tests for AgentConfig value object."""
    
    def test_create_minimal_config(self):
        """Test creating config with minimal parameters."""
        # Act
        config = AgentConfig.create(
            agent_id="agent-001",
            role="DEV",
            model="test-model",
            vllm_url="http://vllm:8000",
            nats_url="nats://nats:4222",
        )
        
        # Assert
        assert config.agent_id == "agent-001"
        assert config.role == AgentRole.DEV
        assert config.model == "test-model"
        assert config.vllm_url == "http://vllm:8000"
        assert config.nats_url == "nats://nats:4222"
        assert config.temperature == 0.7  # default
        assert config.max_tokens == 2048  # default
        assert config.timeout == 60  # default
        assert config.workspace_path is None
        assert config.enable_tools is False
    
    def test_create_full_config(self):
        """Test creating config with all parameters."""
        # Act
        config = AgentConfig.create(
            agent_id="agent-002",
            role="QA",
            model="custom-model",
            vllm_url="http://custom-vllm:9000",
            nats_url="nats://custom-nats:5555",
            temperature=0.9,
            max_tokens=4096,
            timeout=120,
            workspace_path=Path("/workspace/project"),
            enable_tools=True,
        )
        
        # Assert
        assert config.agent_id == "agent-002"
        assert config.role == AgentRole.QA
        assert config.model == "custom-model"
        assert config.temperature == 0.9
        assert config.max_tokens == 4096
        assert config.timeout == 120
        assert config.workspace_path == Path("/workspace/project")
        assert config.enable_tools is True
    
    def test_create_with_string_role(self):
        """Test that string roles are converted to AgentRole enum."""
        # Act
        config = AgentConfig.create(
            agent_id="agent-003",
            role="ARCHITECT",
            model="test-model",
            vllm_url="http://vllm:8000",
            nats_url="nats://nats:4222",
        )
        
        # Assert
        assert config.role == AgentRole.ARCHITECT
        assert isinstance(config.role, AgentRole)
    
    @pytest.mark.skip(reason="AgentConfig validation not fully implemented yet")
    def test_create_with_invalid_role_raises_error(self):
        """Test that invalid role raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid role"):
            AgentConfig.create(
                agent_id="agent-004",
                role="INVALID_ROLE",
                model="test-model",
                vllm_url="http://vllm:8000",
                nats_url="nats://nats:4222",
            )
    
    def test_config_is_immutable(self):
        """Test that config is frozen (immutable)."""
        # Arrange
        config = AgentConfig.create(
            agent_id="agent-005",
            role="DEV",
            model="test-model",
            vllm_url="http://vllm:8000",
            nats_url="nats://nats:4222",
        )
        
        # Act & Assert
        with pytest.raises(Exception):  # dataclass frozen raises FrozenInstanceError
            config.agent_id = "modified"
    
    @pytest.mark.skip(reason="AgentConfig.to_dict() implementation needs review")
    def test_to_dict(self):
        """Test serialization to dictionary."""
        # Arrange
        config = AgentConfig.create(
            agent_id="agent-006",
            role="DEVOPS",
            model="test-model",
            vllm_url="http://vllm:8000",
            nats_url="nats://nats:4222",
            temperature=0.8,
            max_tokens=1024,
        )
        
        # Act
        result = config.to_dict()
        
        # Assert
        assert result["agent_id"] == "agent-006"
        assert result["role"] == "DEVOPS"
        assert result["model"] == "test-model"
        assert result["vllm_url"] == "http://vllm:8000"
        assert result["nats_url"] == "nats://nats:4222"
        assert result["temperature"] == 0.8
        assert result["max_tokens"] == 1024
    
    @pytest.mark.skip(reason="AgentConfig.mode_description() not implemented")
    def test_mode_description_without_tools(self):
        """Test mode description for text-only config."""
        # Arrange
        config = AgentConfig.create(
            agent_id="agent-007",
            role="DEV",
            model="test-model",
            vllm_url="http://vllm:8000",
            nats_url="nats://nats:4222",
            enable_tools=False,
        )
        
        # Act
        description = config.mode_description()
        
        # Assert
        assert "text-only" in description.lower()
    
    @pytest.mark.skip(reason="AgentConfig.mode_description() not implemented")
    def test_mode_description_with_tools(self):
        """Test mode description for tool-enabled config."""
        # Arrange
        config = AgentConfig.create(
            agent_id="agent-008",
            role="DEV",
            model="test-model",
            vllm_url="http://vllm:8000",
            nats_url="nats://nats:4222",
            workspace_path=Path("/workspace"),
            enable_tools=True,
        )
        
        # Act
        description = config.mode_description()
        
        # Assert
        assert "tools enabled" in description.lower() or "execution" in description.lower()
    
    def test_workspace_path_converted_to_path(self):
        """Test that workspace_path string is converted to Path."""
        # Act
        config = AgentConfig.create(
            agent_id="agent-009",
            role="DEV",
            model="test-model",
            vllm_url="http://vllm:8000",
            nats_url="nats://nats:4222",
            workspace_path="/workspace/string/path",
        )
        
        # Assert
        assert isinstance(config.workspace_path, Path)
        assert str(config.workspace_path) == "/workspace/string/path"

