"""Tests for AgentType entity."""

import pytest

from services.orchestrator.domain.entities import AgentType


class TestAgentType:
    """Test suite for AgentType entity."""
    
    def test_from_string_vllm(self):
        """Test converting VLLM string to AgentType."""
        agent_type = AgentType.from_string("RAY_VLLM")
        assert agent_type == AgentType.VLLM
    
    def test_from_string_case_insensitive(self):
        """Test case insensitive conversion."""
        agent_type = AgentType.from_string("ray_vllm")
        assert agent_type == AgentType.VLLM
    
    def test_from_string_mock_raises(self):
        """Test that MOCK agent type raises ValueError."""
        with pytest.raises(ValueError, match="not allowed in production"):
            AgentType.from_string("MOCK")
    
    def test_from_string_invalid_raises(self):
        """Test that invalid agent type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid agent type"):
            AgentType.from_string("INVALID_TYPE")

