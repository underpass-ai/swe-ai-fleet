"""Integration tests for ModelAgentAdapter with models/ bounded context."""

from unittest.mock import Mock, patch

import pytest
from core.orchestrator.domain.agents.agent_factory import AgentFactory, AgentType
from core.orchestrator.domain.agents.model_adapter import ModelAgentAdapter
from core.orchestrator.domain.tasks.task_constraints import TaskConstraints


class TestModelAgentAdapterIntegration:
    """Integration tests for ModelAgentAdapter."""
    
    @pytest.fixture
    def mock_model(self):
        """Create a mock Model instance."""
        model = Mock()
        model.infer.return_value = "This is a test response from the model."
        return model
    
    @pytest.fixture
    def constraints(self):
        """Create TaskConstraints for testing."""
        return TaskConstraints(
            rubric="quality: High quality\nperformance: Fast execution",
            architect_rubric="architecture: Clean design",
            cluster_spec="k_value: 3",
            additional_constraints=["Requirement 1", "Requirement 2"]
        )
    
    def test_model_agent_adapter_creation(self, mock_model):
        """Test ModelAgentAdapter creation."""
        adapter = ModelAgentAdapter(
            model=mock_model,
            agent_id="test-agent-001",
            role="DEV",
            temperature=0.7,
            max_tokens=1024,
            timeout=30,
        )
        
        assert adapter.model == mock_model
        assert adapter.agent_id == "test-agent-001"
        assert adapter.role == "DEV"
        assert adapter.temperature == 0.7
        assert adapter.max_tokens == 1024
        assert adapter.timeout == 30
    
    def test_model_agent_adapter_generate(self, mock_model, constraints):
        """Test ModelAgentAdapter generate method."""
        adapter = ModelAgentAdapter(
            model=mock_model,
            agent_id="test-agent-001",
            role="DEV",
        )
        
        result = adapter.generate("Implement user login", constraints, diversity=True)
        
        # Verify model.infer was called
        mock_model.infer.assert_called_once()
        call_args = mock_model.infer.call_args
        
        assert "prompt" in call_args.kwargs
        assert "messages" in call_args.kwargs
        assert abs(call_args.kwargs["temperature"] - 0.7) < 0.001
        
        # Verify result structure
        assert result["content"] == "This is a test response from the model."
        assert result["metadata"]["agent_id"] == "test-agent-001"
        assert result["metadata"]["role"] == "DEV"
        assert result["metadata"]["diversity"] is True
    
    def test_model_agent_adapter_critique(self, mock_model):
        """Test ModelAgentAdapter critique method."""
        adapter = ModelAgentAdapter(
            model=mock_model,
            agent_id="test-agent-001",
            role="QA",
        )
        
        rubric = {"quality": "High quality", "testing": "Comprehensive tests"}
        result = adapter.critique("Test proposal", rubric)
        
        # Verify model.infer was called
        mock_model.infer.assert_called_once()
        assert result == "This is a test response from the model."
    
    def test_model_agent_adapter_revise(self, mock_model):
        """Test ModelAgentAdapter revise method."""
        adapter = ModelAgentAdapter(
            model=mock_model,
            agent_id="test-agent-001",
            role="DEV",
        )
        
        result = adapter.revise("Original content", "Add error handling")
        
        # Verify model.infer was called
        mock_model.infer.assert_called_once()
        assert result == "This is a test response from the model."
    
    def test_model_agent_adapter_fallback_on_error(self, constraints):
        """Test ModelAgentAdapter fallback behavior on model error."""
        mock_model = Mock()
        mock_model.infer.side_effect = Exception("Model error")
        
        adapter = ModelAgentAdapter(
            model=mock_model,
            agent_id="test-agent-001",
            role="DEV",
        )
        
        result = adapter.generate("Test task", constraints)
        
        # Should return fallback proposal
        assert "Fallback Proposal" in result["content"]
        assert result["metadata"]["error"] == "Model unavailable"
        assert result["metadata"]["model_type"] == "fallback"
    
    def test_agent_factory_creates_model_agent(self):
        """Test that AgentFactory creates ModelAgentAdapter correctly."""
        with patch('core.agents_and_tools.adapters.model_loaders.get_model_from_env') as mock_get_model:
            mock_model = Mock()
            mock_get_model.return_value = mock_model
            
            agent = AgentFactory.create_agent(
                agent_id="test-model-001",
                role="DEV",
                agent_type=AgentType.MODEL,
                temperature=0.8,
                max_tokens=2048,
            )
            
            assert isinstance(agent, ModelAgentAdapter)
            assert agent.agent_id == "test-model-001"
            assert agent.role == "DEV"
            assert abs(agent.temperature - 0.8) < 0.001
            assert agent.max_tokens == 2048
    
    def test_agent_factory_creates_model_agent_with_profile(self):
        """Test that AgentFactory creates ModelAgentAdapter with profile."""
        with patch('core.agents_and_tools.adapters.model_loaders.get_model_from_env') as mock_get_model:
            mock_model = Mock()
            mock_get_model.return_value = mock_model
            
            # Mock profile loading
            mock_profile = {
                "name": "developer",
                "model": "test-model",
                "context_window": 32768,
                "temperature": 0.7,
                "max_tokens": 4096,
            }
            
            with patch('builtins.open', create=True), \
                 patch('yaml.safe_load', return_value=mock_profile):
                agent = AgentFactory.create_agent(
                    agent_id="test-model-001",
                    role="DEV",
                    agent_type=AgentType.MODEL,
                    profile_path="profiles/developer.yaml",
                )
                
                assert isinstance(agent, ModelAgentAdapter)
                assert agent.agent_id == "test-model-001"
                assert agent.role == "DEV"
    
    def test_create_model_agent_from_profile_function(self):
        """Test create_model_agent_from_profile function."""
        with patch('core.agents_and_tools.adapters.model_loaders.get_model_from_env') as mock_get_model:
            mock_model = Mock()
            mock_get_model.return_value = mock_model
            
            # Mock profile content
            mock_profile = {
                "name": "developer",
                "model": "deepseek-coder:33b",
                "context_window": 32768,
                "temperature": 0.7,
                "max_tokens": 4096,
            }
            
            # Mock file reading
            mock_file_content = """
name: developer
model: deepseek-coder:33b
context_window: 32768
temperature: 0.7
max_tokens: 4096
"""
            
            with patch('builtins.open', mock_open(mock_file_content)):
                with patch('yaml.safe_load', return_value=mock_profile):
                    from core.orchestrator.domain.agents.model_adapter import (
                        create_model_agent_from_profile,
                    )
                    
                    agent = create_model_agent_from_profile(
                        profile_path="profiles/developer.yaml",
                        agent_id="test-profile-001",
                        role="DEV",
                    )
                    
                    assert isinstance(agent, ModelAgentAdapter)
                    assert agent.agent_id == "test-profile-001"
                    assert agent.role == "DEV"
    
    def test_string_representations(self, mock_model):
        """Test string representations of ModelAgentAdapter."""
        adapter = ModelAgentAdapter(
            model=mock_model,
            agent_id="test-agent-001",
            role="DEV",
        )
        
        repr_str = repr(adapter)
        assert "ModelAgentAdapter" in repr_str
        assert "test-agent-001" in repr_str
        assert "DEV" in repr_str
        
        str_repr = str(adapter)
        assert "test-agent-001" in str_repr
        assert "DEV" in str_repr


def mock_open(content):
    """Helper function to mock file opening."""
    from unittest.mock import mock_open
    return mock_open(read_data=content)
