"""Tests for AgentConfig entity."""

import pytest

from services.orchestrator.domain.entities import AgentConfig


class TestAgentConfig:
    """Test suite for AgentConfig entity."""
    
    def test_creation(self):
        """Test creating an AgentConfig."""
        config = AgentConfig(
            agent_id="agent-001",
            role="Coder",
            vllm_url="http://vllm:8000",
            model="Qwen/Qwen3-0.6B",
            temperature=0.7
        )
        
        assert config.agent_id == "agent-001"
        assert config.role == "Coder"
        assert config.vllm_url == "http://vllm:8000"
        assert config.model == "Qwen/Qwen3-0.6B"
        assert config.temperature == pytest.approx(0.7)
        assert config.extra_params is None
    
    def test_to_dict(self):
        """Test converting AgentConfig to dict."""
        config = AgentConfig(
            agent_id="agent-001",
            role="Coder",
            vllm_url="http://vllm:8000",
            model="gpt-4",
            temperature=0.9
        )
        
        result = config.to_dict()
        
        assert result["agent_id"] == "agent-001"
        assert result["role"] == "Coder"
        assert result["vllm_url"] == "http://vllm:8000"
        assert result["model"] == "gpt-4"
        assert result["temperature"] == pytest.approx(0.9)
    
    def test_to_dict_with_extra_params(self):
        """Test to_dict includes extra_params."""
        config = AgentConfig(
            agent_id="agent-001",
            role="Coder",
            vllm_url="http://vllm:8000",
            model="gpt-4",
            extra_params={"max_tokens": 2048, "timeout": 30}
        )
        
        result = config.to_dict()
        
        assert result["max_tokens"] == 2048
        assert result["timeout"] == 30
    
    def test_from_dict(self):
        """Test creating AgentConfig from dict."""
        data = {
            "agent_id": "agent-002",
            "role": "Reviewer",
            "vllm_url": "http://vllm:8001",
            "model": "llama2",
            "temperature": 0.5,
            "max_tokens": 1024
        }
        
        config = AgentConfig.from_dict(data.copy())
        
        assert config.agent_id == "agent-002"
        assert config.role == "Reviewer"
        assert config.vllm_url == "http://vllm:8001"
        assert config.model == "llama2"
        assert config.temperature == pytest.approx(0.5)
        assert config.extra_params == {"max_tokens": 1024}
    
    def test_with_overrides(self):
        """Test creating new config with overrides."""
        original = AgentConfig(
            agent_id="agent-001",
            role="Coder",
            vllm_url="http://vllm:8000",
            model="gpt-4",
            temperature=0.7
        )
        
        modified = original.with_overrides(temperature=0.9, model="gpt-3.5")
        
        # Original unchanged
        assert original.temperature == pytest.approx(0.7)
        assert original.model == "gpt-4"
        
        # Modified has new values
        assert modified.temperature == pytest.approx(0.9)
        assert modified.model == "gpt-3.5"
        assert modified.agent_id == "agent-001"  # Unchanged fields preserved

