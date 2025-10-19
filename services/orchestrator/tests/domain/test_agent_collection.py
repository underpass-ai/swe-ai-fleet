"""Tests for AgentCollection entity."""

import pytest

from services.orchestrator.domain.entities import AgentCollection


class MockAgent:
    """Mock agent for testing."""
    
    def __init__(self, agent_id, role):
        self.agent_id = agent_id
        self.role = role


class TestAgentCollection:
    """Test suite for AgentCollection entity."""
    
    def test_creation_empty(self):
        """Test creating empty collection."""
        collection = AgentCollection()
        
        assert collection.count == 0
        assert collection.is_empty is True
        assert len(collection) == 0
    
    def test_add_agent(self):
        """Test adding agent to collection."""
        collection = AgentCollection()
        agent = MockAgent("agent-001", "Coder")
        
        collection.add_agent(agent, "agent-001")
        
        assert collection.count == 1
        assert collection.is_empty is False
        assert "agent-001" in collection
        assert collection.has_agent("agent-001") is True
    
    def test_add_duplicate_agent_raises(self):
        """Test adding duplicate agent raises ValueError."""
        collection = AgentCollection()
        agent = MockAgent("agent-001", "Coder")
        
        collection.add_agent(agent, "agent-001")
        
        with pytest.raises(ValueError, match="already exists"):
            collection.add_agent(agent, "agent-001")
    
    def test_remove_agent(self):
        """Test removing agent from collection."""
        collection = AgentCollection()
        agent = MockAgent("agent-001", "Coder")
        
        collection.add_agent(agent, "agent-001")
        collection.remove_agent("agent-001")
        
        assert collection.count == 0
        assert collection.has_agent("agent-001") is False
    
    def test_remove_nonexistent_agent_raises(self):
        """Test removing non-existent agent raises ValueError."""
        collection = AgentCollection()
        
        with pytest.raises(ValueError, match="not found"):
            collection.remove_agent("agent-999")
    
    def test_get_agent_by_id(self):
        """Test getting agent by ID."""
        collection = AgentCollection()
        agent = MockAgent("agent-001", "Coder")
        
        collection.add_agent(agent, "agent-001")
        retrieved = collection.get_agent_by_id("agent-001")
        
        assert retrieved is agent
        assert retrieved.agent_id == "agent-001"
    
    def test_get_nonexistent_agent_raises(self):
        """Test getting non-existent agent raises ValueError."""
        collection = AgentCollection()
        
        with pytest.raises(ValueError, match="not found"):
            collection.get_agent_by_id("agent-999")
    
    def test_clear(self):
        """Test clearing all agents."""
        collection = AgentCollection()
        collection.add_agent(MockAgent("agent-001", "Coder"), "agent-001")
        collection.add_agent(MockAgent("agent-002", "Reviewer"), "agent-002")
        
        collection.clear()
        
        assert collection.count == 0
        assert collection.is_empty is True
    
    def test_get_all_ids(self):
        """Test getting all agent IDs."""
        collection = AgentCollection()
        collection.add_agent(MockAgent("agent-001", "Coder"), "agent-001")
        collection.add_agent(MockAgent("agent-002", "Reviewer"), "agent-002")
        
        ids = collection.get_all_ids()
        
        assert len(ids) == 2
        assert "agent-001" in ids
        assert "agent-002" in ids
    
    def test_get_all_agents(self):
        """Test getting all agents."""
        collection = AgentCollection()
        agent1 = MockAgent("agent-001", "Coder")
        agent2 = MockAgent("agent-002", "Reviewer")
        
        collection.add_agent(agent1, "agent-001")
        collection.add_agent(agent2, "agent-002")
        
        agents = collection.get_all_agents()
        
        assert len(agents) == 2
        assert agent1 in agents
        assert agent2 in agents
    
    def test_to_dict(self):
        """Test converting collection to dict."""
        collection = AgentCollection()
        collection.add_agent(MockAgent("agent-001", "Coder"), "agent-001")
        
        result = collection.to_dict()
        
        assert result["count"] == 1
        assert "agent-001" in result["agent_ids"]
    
    def test_iteration(self):
        """Test iterating over collection."""
        collection = AgentCollection()
        agent1 = MockAgent("agent-001", "Coder")
        agent2 = MockAgent("agent-002", "Reviewer")
        
        collection.add_agent(agent1, "agent-001")
        collection.add_agent(agent2, "agent-002")
        
        agents = list(collection)
        
        assert len(agents) == 2
        assert agent1 in agents
        assert agent2 in agents

