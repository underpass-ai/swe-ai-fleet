"""Unit tests for VLLMAgent."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from swe_ai_fleet.orchestrator.domain.agents.vllm_agent import VLLMAgent, VLLMAgent
from swe_ai_fleet.orchestrator.domain.tasks.task_constraints import TaskConstraints


class TestVLLMAgent:
    """Test cases for VLLMAgent."""
    
    @pytest.fixture
    def agent(self):
        """Create a VLLMAgent instance for testing."""
        return VLLMAgent(
            agent_id="test-agent-001",
            role="DEV",
            vllm_url="http://localhost:8000",
            model="test-model",
            temperature=0.7,
            max_tokens=1024,
            timeout=30,
        )
    
    @pytest.fixture
    def async_agent(self):
        """Create an VLLMAgent instance for testing."""
        return VLLMAgent(
            agent_id="test-agent-001",
            role="DEV",
            vllm_url="http://localhost:8000",
            model="test-model",
            temperature=0.7,
            max_tokens=1024,
            timeout=30,
        )
    
    @pytest.fixture
    def constraints(self):
        """Create TaskConstraints for testing."""
        constraints = Mock(spec=TaskConstraints)
        constraints.get_rubric.return_value = {
            "code_quality": "High quality code",
            "testing": "Comprehensive tests",
            "documentation": "Clear documentation"
        }
        constraints.get_architect_rubric.return_value = {"k": 3}
        constraints.get_cluster_spec.return_value = None
        constraints.get_k_value.return_value = 3
        return constraints
    
    def test_agent_initialization(self, agent):
        """Test agent initialization."""
        assert agent.agent_id == "test-agent-001"
        assert agent.role == "DEV"
        assert agent.vllm_url == "http://localhost:8000"
        assert agent.model == "test-model"
        assert agent.temperature == 0.7
        assert agent.max_tokens == 1024
        assert agent.timeout == 30
        assert agent.chat_endpoint == "http://localhost:8000/v1/chat/completions"
        assert agent.completions_endpoint == "http://localhost:8000/v1/completions"
    
    def test_agent_string_representations(self, agent):
        """Test string representations."""
        repr_str = repr(agent)
        assert "VLLMAgent" in repr_str
        assert "test-agent-001" in repr_str
        assert "DEV" in repr_str
        assert "test-model" in repr_str
        
        str_repr = str(agent)
        assert "test-agent-001" in str_repr
        assert "DEV" in str_repr
        assert "test-model" in str_repr
        assert "localhost:8000" in str_repr
    
    @pytest.mark.asyncio
    async def test_generate_success(self, agent, constraints):
        """Test successful proposal generation."""
        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": "This is a test proposal for the given task."
                    }
                }
            ]
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response_obj = AsyncMock()
            mock_response_obj.status = 200
            mock_response_obj.json = AsyncMock(return_value=mock_response)
            
            mock_post.return_value.__aenter__.return_value = mock_response_obj
            
            result = await agent.generate("Test task", constraints, diversity=True)
            
            assert result["content"] == "This is a test proposal for the given task."
            assert result["metadata"]["agent_id"] == "test-agent-001"
            assert result["metadata"]["role"] == "DEV"
            assert result["metadata"]["model"] == "test-model"
            assert result["metadata"]["diversity"] is True
            assert result["metadata"]["temperature"] == 0.7
    
    @pytest.mark.asyncio
    async def test_generate_api_error(self, agent, constraints):
        """Test proposal generation with API error."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response_obj = AsyncMock()
            mock_response_obj.status = 500
            mock_response_obj.text = AsyncMock(return_value="Internal Server Error")
            
            mock_post.return_value.__aenter__.return_value = mock_response_obj
            
            result = await agent.generate("Test task", constraints)
            
            # Should return fallback proposal
            assert "Fallback Proposal" in result["content"]
            assert result["metadata"]["error"] == "vLLM unavailable"
    
    @pytest.mark.asyncio
    async def test_generate_exception(self, agent, constraints):
        """Test proposal generation with exception."""
        with patch('aiohttp.ClientSession.post', side_effect=Exception("Network error")):
            result = await agent.generate("Test task", constraints)
            
            # Should return fallback proposal
            assert "Fallback Proposal" in result["content"]
            assert result["metadata"]["error"] == "vLLM unavailable"
    
    @pytest.mark.asyncio
    async def test_critique_success(self, agent):
        """Test successful critique generation."""
        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": "This proposal looks good but could use more detail."
                    }
                }
            ]
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response_obj = AsyncMock()
            mock_response_obj.status = 200
            mock_response_obj.json = AsyncMock(return_value=mock_response)
            
            mock_post.return_value.__aenter__.return_value = mock_response_obj
            
            rubric = {"quality": "High quality"}
            result = await agent.critique("Test proposal", rubric)
            
            assert result == "This proposal looks good but could use more detail."
    
    @pytest.mark.asyncio
    async def test_critique_error(self, agent):
        """Test critique generation with error."""
        with patch('aiohttp.ClientSession.post', side_effect=Exception("Network error")):
            rubric = {"quality": "High quality"}
            result = await agent.critique("Test proposal", rubric)
            
            assert "Unable to provide critique due to error" in result
            assert "Network error" in result
    
    @pytest.mark.asyncio
    async def test_revise_success(self, agent):
        """Test successful revision."""
        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": "Revised proposal with improvements based on feedback."
                    }
                }
            ]
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response_obj = AsyncMock()
            mock_response_obj.status = 200
            mock_response_obj.json = AsyncMock(return_value=mock_response)
            
            mock_post.return_value.__aenter__.return_value = mock_response_obj
            
            result = await agent.revise("Original content", "Add more details")
            
            assert result == "Revised proposal with improvements based on feedback."
    
    @pytest.mark.asyncio
    async def test_revise_error(self, agent):
        """Test revision with error."""
        with patch('aiohttp.ClientSession.post', side_effect=Exception("Network error")):
            result = await agent.revise("Original content", "Add more details")
            
            assert "Original content" in result
            assert "Revision failed due to error" in result
            assert "Network error" in result
    
    def test_build_system_prompt(self, agent, constraints):
        """Test system prompt building."""
        prompt = agent._build_system_prompt(constraints, diversity=True)
        
        assert "test-agent-001" in prompt
        assert "DEV" in prompt
        assert "code_quality" in prompt
        assert "testing" in prompt
        assert "documentation" in prompt
        assert "creative and explore diverse approaches" in prompt
    
    def test_build_task_prompt(self, agent, constraints):
        """Test task prompt building."""
        prompt = agent._build_task_prompt("Test task", constraints)
        
        assert "Test task" in prompt
        assert "Please provide a detailed proposal" in prompt
    
    def test_fallback_proposal(self, agent, constraints):
        """Test fallback proposal generation."""
        result = agent._fallback_proposal("Test task", constraints, diversity=True)
        
        assert "Fallback Proposal" in result["content"]
        assert "test-agent-001" in result["content"]
        assert "DEV" in result["content"]
        assert "Test task" in result["content"]
        assert result["metadata"]["error"] == "vLLM unavailable"
        assert result["metadata"]["model"] == "fallback"


class TestVLLMAgent:
    """Test cases for VLLMAgent sync wrapper."""
    
    @pytest.fixture
    def async_agent(self):
        """Create an VLLMAgent instance for testing."""
        return VLLMAgent(
            agent_id="test-agent-001",
            role="DEV",
            vllm_url="http://localhost:8000",
            model="test-model",
        )
    
    @pytest.fixture
    def constraints(self):
        """Create TaskConstraints for testing."""
        constraints = Mock(spec=TaskConstraints)
        constraints.get_rubric.return_value = {"quality": "High quality"}
        constraints.get_architect_rubric.return_value = {"k": 3}
        constraints.get_cluster_spec.return_value = None
        constraints.get_k_value.return_value = 3
        return constraints
    
    def test_sync_generate_wrapper(self, async_agent, constraints):
        """Test sync wrapper for generate method."""
        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": "Test proposal content"
                    }
                }
            ]
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response_obj = AsyncMock()
            mock_response_obj.status = 200
            mock_response_obj.json = AsyncMock(return_value=mock_response)
            
            mock_post.return_value.__aenter__.return_value = mock_response_obj
            
            result = async_agent.generate("Test task", constraints)
            
            assert result["content"] == "Test proposal content"
            assert result["metadata"]["agent_id"] == "test-agent-001"
    
    def test_sync_critique_wrapper(self, async_agent):
        """Test sync wrapper for critique method."""
        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": "Test critique content"
                    }
                }
            ]
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response_obj = AsyncMock()
            mock_response_obj.status = 200
            mock_response_obj.json = AsyncMock(return_value=mock_response)
            
            mock_post.return_value.__aenter__.return_value = mock_response_obj
            
            result = async_agent.critique("Test proposal", {"quality": "High"})
            
            assert result == "Test critique content"
    
    def test_sync_revise_wrapper(self, async_agent):
        """Test sync wrapper for revise method."""
        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": "Revised content"
                    }
                }
            ]
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response_obj = AsyncMock()
            mock_response_obj.status = 200
            mock_response_obj.json = AsyncMock(return_value=mock_response)
            
            mock_post.return_value.__aenter__.return_value = mock_response_obj
            
            result = async_agent.revise("Original content", "Feedback")
            
            assert result == "Revised content"
