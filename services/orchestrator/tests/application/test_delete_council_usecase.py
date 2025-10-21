"""Tests for DeleteCouncilUseCase."""

import pytest

from services.orchestrator.application import DeleteCouncilUseCase
from services.orchestrator.domain.entities import CouncilRegistry


class MockCouncil:
    """Mock council for testing."""
    
    def __init__(self, role):
        self.role = role


class MockAgent:
    """Mock agent for testing."""
    
    def __init__(self, agent_id):
        self.agent_id = agent_id


class TestDeleteCouncilUseCase:
    """Test suite for DeleteCouncilUseCase."""
    
    def test_execute_success(self):
        """Test successful council deletion."""
        registry = CouncilRegistry()
        agents = [MockAgent("agent-001"), MockAgent("agent-002")]
        registry.register_council("Coder", MockCouncil("Coder"), agents)
        
        use_case = DeleteCouncilUseCase(council_registry=registry)
        result = use_case.execute(role="Coder")
        
        assert result.role == "Coder"
        assert result.agents_removed == 2
        assert result.success is True
        assert "deleted successfully" in result.message
        assert registry.has_council("Coder") is False
    
    def test_execute_empty_role_raises(self):
        """Test that empty role raises ValueError."""
        registry = CouncilRegistry()
        use_case = DeleteCouncilUseCase(council_registry=registry)
        
        with pytest.raises(ValueError, match="Role cannot be empty"):
            use_case.execute(role="")
    
    def test_execute_whitespace_role_raises(self):
        """Test that whitespace-only role raises ValueError."""
        registry = CouncilRegistry()
        use_case = DeleteCouncilUseCase(council_registry=registry)
        
        with pytest.raises(ValueError, match="Role cannot be empty"):
            use_case.execute(role="   ")
    
    def test_execute_nonexistent_council_raises(self):
        """Test that deleting non-existent council raises ValueError."""
        registry = CouncilRegistry()
        use_case = DeleteCouncilUseCase(council_registry=registry)
        
        with pytest.raises(ValueError, match="not found"):
            use_case.execute(role="NonExistent")

