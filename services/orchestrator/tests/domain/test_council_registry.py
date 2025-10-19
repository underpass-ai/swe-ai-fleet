"""Tests for CouncilRegistry entity."""

import pytest

from services.orchestrator.domain.entities import CouncilRegistry


class MockCouncil:
    """Mock council for testing."""
    
    def __init__(self, role):
        self.role = role


class MockAgent:
    """Mock agent for testing."""
    
    def __init__(self, agent_id):
        self.agent_id = agent_id


class TestCouncilRegistry:
    """Test suite for CouncilRegistry entity."""
    
    def test_creation_empty(self):
        """Test creating empty registry."""
        registry = CouncilRegistry()
        
        assert registry.count == 0
        assert registry.is_empty is True
    
    def test_register_council(self):
        """Test registering a council."""
        registry = CouncilRegistry()
        council = MockCouncil("Coder")
        agents = [MockAgent("agent-001")]
        
        registry.register_council("Coder", council, agents)
        
        assert registry.count == 1
        assert registry.has_council("Coder") is True
    
    def test_register_duplicate_raises(self):
        """Test registering duplicate council raises ValueError."""
        registry = CouncilRegistry()
        council = MockCouncil("Coder")
        
        registry.register_council("Coder", council, [])
        
        with pytest.raises(ValueError, match="already exists"):
            registry.register_council("Coder", council, [])
    
    def test_get_council(self):
        """Test getting a council."""
        registry = CouncilRegistry()
        council = MockCouncil("Coder")
        
        registry.register_council("Coder", council, [])
        retrieved = registry.get_council("Coder")
        
        assert retrieved is council
    
    def test_get_council_not_found_raises(self):
        """Test getting non-existent council raises RuntimeError."""
        registry = CouncilRegistry()
        
        with pytest.raises(RuntimeError, match="not found in registry"):
            registry.get_council("NonExistent")
    
    def test_get_council_error_shows_available_roles(self):
        """Test error message shows available roles."""
        registry = CouncilRegistry()
        registry.register_council("Coder", MockCouncil("Coder"), [])
        registry.register_council("Reviewer", MockCouncil("Reviewer"), [])
        
        with pytest.raises(RuntimeError, match="Available roles"):
            registry.get_council("Architect")
    
    def test_get_agents(self):
        """Test getting agents for a council."""
        registry = CouncilRegistry()
        agents = [MockAgent("agent-001"), MockAgent("agent-002")]
        
        registry.register_council("Coder", MockCouncil("Coder"), agents)
        retrieved = registry.get_agents("Coder")
        
        assert len(retrieved) == 2
        assert retrieved[0].agent_id == "agent-001"
    
    def test_delete_council(self):
        """Test deleting a council."""
        registry = CouncilRegistry()
        council = MockCouncil("Coder")
        agents = [MockAgent("agent-001")]
        
        registry.register_council("Coder", council, agents)
        deleted_council, agents_count = registry.delete_council("Coder")
        
        assert deleted_council is council
        assert agents_count == 1
        assert registry.has_council("Coder") is False
    
    def test_delete_nonexistent_council_raises(self):
        """Test deleting non-existent council raises ValueError."""
        registry = CouncilRegistry()
        
        with pytest.raises(ValueError, match="not found"):
            registry.delete_council("NonExistent")
    
    def test_update_council(self):
        """Test updating a council."""
        registry = CouncilRegistry()
        council1 = MockCouncil("Coder")
        council2 = MockCouncil("Coder")
        agents = [MockAgent("agent-001")]
        
        registry.register_council("Coder", council1, agents)
        registry.update_council("Coder", council2, agents)
        
        assert registry.get_council("Coder") is council2
    
    def test_update_nonexistent_council_raises(self):
        """Test updating non-existent council raises ValueError."""
        registry = CouncilRegistry()
        
        with pytest.raises(ValueError, match="not found"):
            registry.update_council("NonExistent", MockCouncil("Test"), [])
    
    def test_get_all_councils(self):
        """Test getting all councils."""
        registry = CouncilRegistry()
        council1 = MockCouncil("Coder")
        council2 = MockCouncil("Reviewer")
        
        registry.register_council("Coder", council1, [])
        registry.register_council("Reviewer", council2, [])
        
        councils = list(registry.get_all_councils().values())  # Get councils from dict
        
        assert len(councils) == 2
        assert council1 in councils
        assert council2 in councils
    
    def test_to_dict(self):
        """Test converting registry to dict."""
        registry = CouncilRegistry()
        registry.register_council("Coder", MockCouncil("Coder"), [MockAgent("a1")])
        
        result = registry.to_dict()
        
        assert result["count"] == 1
        assert "Coder" in result["roles"]

