"""Tests for VLLMAgentFactoryAdapter."""


from services.orchestrator.infrastructure.adapters import VLLMAgentFactoryAdapter


class TestVLLMAgentFactoryAdapter:
    """Test suite for VLLMAgentFactoryAdapter."""
    
    def test_create_agent_success(self):
        """Test successful agent creation."""
        adapter = VLLMAgentFactoryAdapter()
        
        # Note: AgentFactory integration test would go here
        # For now, just test that the adapter is created
        assert adapter is not None
        assert hasattr(adapter, 'create_agent')
        assert hasattr(adapter, '_agent_factory')
    
    def test_adapter_has_agent_factory(self):
        """Test that adapter initializes with AgentFactory."""
        adapter = VLLMAgentFactoryAdapter()
        
        # Verify the adapter has the _agent_factory attribute
        assert hasattr(adapter, '_agent_factory')
        assert adapter._agent_factory is not None

