"""Tests for CouncilQueryAdapter."""

import pytest

from services.orchestrator.domain.entities import CouncilRegistry
from services.orchestrator.infrastructure.adapters import CouncilQueryAdapter


class MockAgent:
    """Mock agent for testing."""
    
    def __init__(self, agent_id, model="gpt-4"):
        self.agent_id = agent_id
        self.model = model


class MockCouncil:
    """Mock council for testing."""
    
    def __init__(self, role):
        self.role = role


class TestCouncilQueryAdapter:
    """Test suite for CouncilQueryAdapter."""
    
    def test_list_councils_with_agents(self):
        """Test listing councils with agent details."""
        registry = CouncilRegistry()
        agents = [MockAgent("agent-001", "gpt-4")]
        registry.register_council("Coder", MockCouncil("Coder"), agents)
        
        adapter = CouncilQueryAdapter(default_model="Qwen/Qwen3-0.6B")
        result = adapter.list_councils(registry, include_agents=True)
        
        assert len(result) == 1
        assert result[0].role == "Coder"
        assert result[0].model == "gpt-4"
    
    def test_list_councils_without_agents_raises(self):
        """Test listing councils without agents raises RuntimeError."""
        registry = CouncilRegistry()
        adapter = CouncilQueryAdapter(default_model="Qwen/Qwen3-0.6B")
        
        with pytest.raises(RuntimeError, match="include_agents must be True"):
            adapter.list_councils(registry, include_agents=False)
    
    def test_get_council_info(self):
        """Test getting single council info."""
        registry = CouncilRegistry()
        agents = [MockAgent("agent-001", "gpt-4")]
        registry.register_council("Coder", MockCouncil("Coder"), agents)
        
        adapter = CouncilQueryAdapter(default_model="Qwen/Qwen3-0.6B")
        result = adapter.get_council_info(registry, "Coder", include_agents=True)
        
        assert result.role == "Coder"
        assert result.num_agents == 1
    
    def test_get_council_info_without_agents_raises(self):
        """Test getting council info without agents raises RuntimeError."""
        registry = CouncilRegistry()
        adapter = CouncilQueryAdapter(default_model="Qwen/Qwen3-0.6B")
        
        with pytest.raises(RuntimeError, match="include_agents must be True"):
            adapter.get_council_info(registry, "Coder", include_agents=False)
    
    def test_get_council_info_not_found_raises(self):
        """Test getting non-existent council raises ValueError."""
        registry = CouncilRegistry()
        adapter = CouncilQueryAdapter(default_model="Qwen/Qwen3-0.6B")
        
        with pytest.raises(ValueError, match="Council for role NonExistent not found"):
            adapter.get_council_info(registry, "NonExistent", include_agents=True)
    
    def test_build_council_info_empty_agents_raises(self):
        """Test building council info with empty agents raises RuntimeError."""
        adapter = CouncilQueryAdapter(default_model="Qwen/Qwen3-0.6B")
        
        with pytest.raises(RuntimeError, match="has no agents"):
            adapter._build_council_info("Coder", [], include_agents=True)
    
    def test_build_council_info_unknown_model_raises(self):
        """Test building council info with unknown model raises RuntimeError."""
        class AgentNoModel:
            def __init__(self):
                self.agent_id = "agent-001"
        
        adapter = CouncilQueryAdapter(default_model=None)
        
        with pytest.raises(RuntimeError, match="Cannot determine model"):
            adapter._build_council_info("Coder", [AgentNoModel()], include_agents=True)
    
    def test_build_council_info_uses_default_model(self):
        """Test building council info uses default model for vLLM agents."""
        class VLLMAgent:
            def __init__(self):
                self.agent_id = "agent-001"
                self.vllm_url = "http://vllm:8000"
        
        adapter = CouncilQueryAdapter(default_model="Qwen/Qwen3-0.6B")
        result = adapter._build_council_info("Coder", [VLLMAgent()], include_agents=True)
        
        assert result.model == "Qwen/Qwen3-0.6B"

