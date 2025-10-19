"""Tests for DeliberateCouncilFactoryAdapter."""


from services.orchestrator.infrastructure.adapters import DeliberateCouncilFactoryAdapter


class MockAgent:
    """Mock agent for testing."""
    
    def __init__(self, agent_id):
        self.agent_id = agent_id


class MockScoring:
    """Mock scoring tool for testing."""
    
    def score(self, proposal):
        return 1.0


class TestDeliberateCouncilFactoryAdapter:
    """Test suite for DeliberateCouncilFactoryAdapter."""
    
    def test_adapter_initialization(self):
        """Test that adapter initializes correctly."""
        adapter = DeliberateCouncilFactoryAdapter()
        
        # Verify the adapter has the Deliberate class
        assert hasattr(adapter, '_deliberate_class')
        assert adapter._deliberate_class is not None
    
    def test_create_council_success(self):
        """Test successful council creation."""
        adapter = DeliberateCouncilFactoryAdapter()
        agents = [MockAgent("agent-001"), MockAgent("agent-002")]
        scoring = MockScoring()
        
        council = adapter.create_council(
            agents=agents,
            tooling=scoring,
            rounds=1
        )
        
        # Verify council was created
        assert council is not None
        # Deliberate councils may not have direct 'agents' attribute
        assert hasattr(council, 'execute') or hasattr(council, 'agents')
    
    def test_create_council_with_empty_agents_list(self):
        """Test creating council with empty agents list."""
        adapter = DeliberateCouncilFactoryAdapter()
        scoring = MockScoring()
        
        # Should create council even with empty agents (validation is in use case)
        council = adapter.create_council(
            agents=[],
            tooling=scoring,
            rounds=1
        )
        
        assert council is not None

