"""Tests for GenerateProposal use case."""

from unittest.mock import AsyncMock

import pytest
from core.ray_jobs.application import GenerateProposal
from core.ray_jobs.domain import AgentConfig, VLLMResponse


class TestGenerateProposal:
    """Tests for GenerateProposal use case."""
    
    @pytest.fixture
    def config(self):
        """Create agent config for testing."""
        return AgentConfig.create(
            agent_id="agent-test-001",
            role="DEV",
            model="test-model",
            vllm_url="http://vllm:8000",
            nats_url="nats://nats:4222",
            temperature=0.7,
            max_tokens=1024,
        )
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        client = AsyncMock()
        return client
    
    @pytest.mark.asyncio
    async def test_execute_success(self, config, mock_llm_client):
        """Test successful proposal generation."""
        # Arrange
        mock_response = VLLMResponse(
            content="Generated proposal content",
            author_id="agent-test-001",
            author_role="DEV",
            model="test-model",
            temperature=0.7,
            tokens=150,
        )
        mock_llm_client.generate = AsyncMock(return_value=mock_response)
        
        use_case = GenerateProposal(
            config=config,
            llm_client=mock_llm_client,
        )
        
        # Act
        result = await use_case.execute(
            task="Implement factorial function",
            constraints={"rubric": "Clean code"},
            diversity=False,
        )
        
        # Assert
        assert result["content"] == "Generated proposal content"
        assert result["author_id"] == "agent-test-001"
        assert result["author_role"] == "DEV"
        assert result["tokens"] == 150
        
        # Verify LLM client was called
        mock_llm_client.generate.assert_called_once()
        call_args = mock_llm_client.generate.call_args[0][0]  # VLLMRequest
        assert call_args.model == "test-model"
        assert call_args.temperature == 0.7
        assert call_args.max_tokens == 1024
    
    @pytest.mark.asyncio
    async def test_execute_with_diversity(self, config, mock_llm_client):
        """Test proposal generation with diversity flag."""
        # Arrange
        mock_response = VLLMResponse(
            content="Diverse proposal",
            author_id="agent-test-001",
            author_role="DEV",
            model="test-model",
            temperature=0.91,  # 0.7 * 1.3
            tokens=100,
        )
        mock_llm_client.generate = AsyncMock(return_value=mock_response)
        
        use_case = GenerateProposal(
            config=config,
            llm_client=mock_llm_client,
        )
        
        # Act
        result = await use_case.execute(
            task="Test task",
            constraints={},
            diversity=True,
        )
        
        # Assert
        assert result["content"] == "Diverse proposal"
        
        # Verify temperature was increased
        call_args = mock_llm_client.generate.call_args[0][0]
        assert call_args.temperature == 0.7 * 1.3
    
    @pytest.mark.asyncio
    async def test_execute_with_constraints(self, config, mock_llm_client):
        """Test proposal generation with constraints."""
        # Arrange
        mock_response = VLLMResponse(
            content="Constrained proposal",
            author_id="agent-test-001",
            author_role="DEV",
            model="test-model",
            temperature=0.7,
            tokens=200,
        )
        mock_llm_client.generate = AsyncMock(return_value=mock_response)
        
        use_case = GenerateProposal(
            config=config,
            llm_client=mock_llm_client,
        )
        
        constraints = {
            "rubric": "Must use type hints",
            "requirements": ["Add docstrings", "Follow PEP8"],
            "metadata": {"language": "Python", "framework": "pytest"},
        }
        
        # Act
        result = await use_case.execute(
            task="Write tests",
            constraints=constraints,
            diversity=False,
        )
        
        # Assert
        assert result["content"] == "Constrained proposal"
        
        # Verify VLLMRequest includes constraints in prompts
        call_args = mock_llm_client.generate.call_args[0][0]
        # System prompt should include rubric and requirements
        assert "type hints" in call_args.messages[0].content.lower()
        # Task prompt should include metadata
        assert "pytest" in call_args.messages[1].content.lower()
    
    @pytest.mark.asyncio
    async def test_execute_llm_error(self, config, mock_llm_client):
        """Test handling of LLM client errors."""
        # Arrange
        mock_llm_client.generate = AsyncMock(
            side_effect=RuntimeError("LLM API error")
        )
        
        use_case = GenerateProposal(
            config=config,
            llm_client=mock_llm_client,
        )
        
        # Act & Assert
        with pytest.raises(RuntimeError, match="LLM API error"):
            await use_case.execute(
                task="Test task",
                constraints={},
                diversity=False,
            )

