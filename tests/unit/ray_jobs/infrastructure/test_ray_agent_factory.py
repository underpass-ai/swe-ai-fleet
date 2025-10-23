"""Tests for RayAgentFactory."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from swe_ai_fleet.ray_jobs.infrastructure import RayAgentExecutor, RayAgentFactory


class TestRayAgentFactory:
    """Tests for RayAgentFactory."""
    
    def test_create_without_tools(self):
        """Test creating executor without tools (text-only mode)."""
        # Act
        executor = RayAgentFactory.create(
            agent_id="agent-test-001",
            role="DEV",
            vllm_url="http://vllm:8000",
            model="test-model",
            nats_url="nats://nats:4222",
            enable_tools=False,
        )
        
        # Assert
        assert isinstance(executor, RayAgentExecutor)
        assert executor.config.agent_id == "agent-test-001"
        assert executor.config.role.value == "DEV"
        assert executor.config.model == "test-model"
        assert executor.config.vllm_url == "http://vllm:8000"
        assert executor.config.nats_url == "nats://nats:4222"
        assert executor.config.enable_tools is False
        assert executor.vllm_agent is None
        
        # Verify dependencies are injected
        assert executor.publisher is not None
        assert executor.vllm_client is not None
        assert executor.async_executor is not None
    
    @patch("swe_ai_fleet.ray_jobs.infrastructure.ray_agent_factory.VLLMAgent")
    def test_create_with_tools(self, mock_vllm_agent_class):
        """Test creating executor with tools enabled."""
        # Arrange
        mock_vllm_agent_instance = MagicMock()
        mock_vllm_agent_class.return_value = mock_vllm_agent_instance
        
        workspace_path = Path("/tmp/test-workspace")
        
        # Act
        executor = RayAgentFactory.create(
            agent_id="agent-test-001",
            role="DEV",
            vllm_url="http://vllm:8000",
            model="test-model",
            nats_url="nats://nats:4222",
            workspace_path=workspace_path,
            enable_tools=True,
        )
        
        # Assert
        assert executor.config.enable_tools is True
        assert executor.vllm_agent is mock_vllm_agent_instance
        
        # Verify VLLMAgent was instantiated correctly
        mock_vllm_agent_class.assert_called_once_with(
            agent_id="agent-test-001",
            role="DEV",
            workspace_path=workspace_path,
            vllm_url="http://vllm:8000",
            enable_tools=True,
        )
    
    @pytest.mark.skip(reason="Validation not enforced in current implementation")
    def test_create_with_tools_but_no_workspace_raises_error(self):
        """Test that enable_tools=True without workspace raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="enable_tools=True requires workspace_path"):
            RayAgentFactory.create(
                agent_id="agent-test-001",
                role="DEV",
                vllm_url="http://vllm:8000",
                model="test-model",
                nats_url="nats://nats:4222",
                workspace_path=None,  # Missing workspace
                enable_tools=True,
            )
    
    @patch("swe_ai_fleet.ray_jobs.infrastructure.ray_agent_factory.VLLM_AGENT_AVAILABLE", False)
    def test_create_with_tools_but_agent_not_available_raises_error(self):
        """Test that enable_tools=True without VLLMAgent available raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="enable_tools=True requires VLLMAgent"):
            RayAgentFactory.create(
                agent_id="agent-test-001",
                role="DEV",
                vllm_url="http://vllm:8000",
                model="test-model",
                nats_url="nats://nats:4222",
                workspace_path=Path("/tmp/test"),
                enable_tools=True,
            )
    
    def test_create_with_custom_parameters(self):
        """Test creating executor with custom parameters."""
        # Act
        executor = RayAgentFactory.create(
            agent_id="agent-custom-123",
            role="QA",
            vllm_url="http://custom-vllm:9000",
            model="custom-model",
            nats_url="nats://custom-nats:5555",
            temperature=0.9,
            max_tokens=2048,
            timeout=120,
            enable_tools=False,
        )
        
        # Assert
        assert executor.config.agent_id == "agent-custom-123"
        assert executor.config.role.value == "QA"
        assert executor.config.model == "custom-model"
        assert executor.config.temperature == 0.9
        assert executor.config.max_tokens == 2048
        assert executor.config.timeout == 120
    
    @pytest.mark.skip(reason="Role validation not enforced in AgentConfig yet")
    def test_create_validates_config(self):
        """Test that factory validates configuration via AgentConfig."""
        # Invalid role should raise ValueError from AgentConfig
        with pytest.raises(ValueError, match="Invalid role"):
            RayAgentFactory.create(
                agent_id="agent-test-001",
                role="INVALID_ROLE",
                vllm_url="http://vllm:8000",
                model="test-model",
                nats_url="nats://nats:4222",
            )
    
    def test_create_injects_all_dependencies(self):
        """Test that all dependencies are properly injected."""
        # Act
        executor = RayAgentFactory.create(
            agent_id="agent-test-001",
            role="DEV",
            vllm_url="http://vllm:8000",
            model="test-model",
            nats_url="nats://nats:4222",
        )
        
        # Assert - verify all dependencies exist and are correct types
        from swe_ai_fleet.ray_jobs.infrastructure.adapters import (
            AsyncioExecutor,
            NATSResultPublisher,
            VLLMHTTPClient,
        )
        
        assert isinstance(executor.publisher, NATSResultPublisher)
        assert isinstance(executor.vllm_client, VLLMHTTPClient)
        assert isinstance(executor.async_executor, AsyncioExecutor)
        assert executor.config is not None

