"""Tests for ExecuteAgentTask use case."""

import pytest
from unittest.mock import AsyncMock, Mock
from pathlib import Path

from core.ray_jobs.application import ExecuteAgentTask
from core.ray_jobs.domain import (
    AgentConfig,
    ExecutionRequest,
    AgentResult,
)


class TestExecuteAgentTask:
    """Tests for ExecuteAgentTask use case."""
    
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
            enable_tools=False,
        )
    
    @pytest.fixture
    def mock_publisher(self):
        """Create mock result publisher."""
        publisher = AsyncMock()
        publisher.connect = AsyncMock()
        publisher.publish_success = AsyncMock()
        publisher.publish_failure = AsyncMock()
        publisher.close = AsyncMock()
        return publisher
    
    @pytest.fixture
    def mock_vllm_client(self):
        """Create mock vLLM client."""
        client = AsyncMock()
        return client
    
    @pytest.fixture
    def execution_request(self):
        """Create execution execution_request for testing."""
        return ExecutionRequest.create(
            task_id="task-123",
            task_description="Test task",
            constraints={"rubric": "Test rubric"},
            diversity=False,
        )
    
    @pytest.mark.asyncio
    async def test_execute_text_only_success(self, config, mock_publisher, mock_vllm_client, execution_request):
        """Test successful text-only execution."""
        # Arrange
        use_case = ExecuteAgentTask(
            config=config,
            publisher=mock_publisher,
            vllm_client=mock_vllm_client,
            vllm_agent=None,  # No tools
        )
        
        # Mock vLLM client response (será llamado internamente por GenerateProposal)
        from core.ray_jobs.domain import VLLMResponse
        mock_response = VLLMResponse(
            content="Test proposal content",
            author_id="agent-test-001",
            author_role="DEV",
            model="test-model",
            temperature=0.7,
            tokens=100,
        )
        mock_vllm_client.generate = AsyncMock(return_value=mock_response)
        
        # Act
        result = await use_case.execute(execution_request)
        
        # Assert
        assert result["status"] == "completed"
        assert result["task_id"] == "task-123"
        assert result["agent_id"] == "agent-test-001"
        assert "proposal" in result
        assert result["proposal"]["content"] == "Test proposal content"
        
        # Verify publisher interactions
        mock_publisher.connect.assert_called_once()
        mock_publisher.publish_success.assert_called_once()
        mock_publisher.close.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires AgentExecutionResult from core.agents")
    async def test_execute_with_tools_success(self, config, mock_publisher, mock_vllm_client, execution_request):
        """Test successful execution with tools (VLLMAgent)."""
        # Arrange
        mock_vllm_agent = AsyncMock()
        
        # Mock VLLMAgent response
        from core.agents_and_tools.agents import AgentResult
        agent_result = AgentResult(
            success=True,
            operations=["git.commit", "files.write"],
            artifacts={"commit_sha": "abc123"},
            audit_trail=["Step 1", "Step 2"],
            error=None,
        )
        mock_vllm_agent.execute_task = AsyncMock(return_value=agent_result)
        
        # Update config to enable tools
        config_with_tools = AgentConfig.create(
            agent_id="agent-test-001",
            role="DEV",
            model="test-model",
            vllm_url="http://vllm:8000",
            nats_url="nats://nats:4222",
            workspace_path=Path("/tmp/test"),
            enable_tools=True,
        )
        
        use_case = ExecuteAgentTask(
            config=config_with_tools,
            publisher=mock_publisher,
            vllm_client=mock_vllm_client,
            vllm_agent=mock_vllm_agent,
        )
        
        # Act
        result = await use_case.execute(execution_request)
        
        # Assert
        assert result["status"] == "completed"
        assert result["task_id"] == "task-123"
        assert len(result["operations"]) == 2
        assert result["artifacts"]["commit_sha"] == "abc123"
        assert len(result["audit_trail"]) == 2
        
        # Verify VLLMAgent was called
        mock_vllm_agent.execute_task.assert_called_once()
        call_args = mock_vllm_agent.execute_task.call_args[1]
        assert call_args["task"] == "Test task"
        
        # Verify publisher interactions
        mock_publisher.connect.assert_called_once()
        mock_publisher.publish_success.assert_called_once()
        mock_publisher.close.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires AgentExecutionResult from core.agents")
    async def test_execute_with_tools_failure(self, config, mock_publisher, mock_vllm_client, execution_request):
        """Test execution with tools that fails."""
        # Arrange
        mock_vllm_agent = AsyncMock()
        
        # Mock VLLMAgent failure  
        from core.agents_and_tools.agents import AgentResult
        agent_result = AgentResult(
            success=False,
            operations=[],
            artifacts={},
            audit_trail=["Step 1", "ERROR"],
            error="Test error message",
        )
        mock_vllm_agent.execute_task = AsyncMock(return_value=agent_result)
        
        config_with_tools = AgentConfig.create(
            agent_id="agent-test-001",
            role="DEV",
            model="test-model",
            vllm_url="http://vllm:8000",
            nats_url="nats://nats:4222",
            workspace_path=Path("/tmp/test"),
            enable_tools=True,
        )
        
        use_case = ExecuteAgentTask(
            config=config_with_tools,
            publisher=mock_publisher,
            vllm_client=mock_vllm_client,
            vllm_agent=mock_vllm_agent,
        )
        
        # Act
        result = await use_case.execute(execution_request)
        
        # Assert
        assert result["status"] == "failed"
        assert "error" in result
        assert "Test error message" in result["error"]
        
        # Verify publisher called publish_failure
        mock_publisher.connect.assert_called_once()
        mock_publisher.publish_failure.assert_called_once()
        mock_publisher.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_exception_handling(self, config, mock_publisher, mock_vllm_client, execution_request):
        """Test exception handling during execution."""
        # Arrange
        mock_vllm_client.generate = AsyncMock(side_effect=RuntimeError("vLLM error"))
        
        use_case = ExecuteAgentTask(
            config=config,
            publisher=mock_publisher,
            vllm_client=mock_vllm_client,
            vllm_agent=None,
        )
        
        # Act
        result = await use_case.execute(execution_request)
        
        # Assert
        assert result["status"] == "failed"
        assert "error" in result
        assert "vLLM error" in result["error"]
        
        # Verify publisher called publish_failure
        mock_publisher.publish_failure.assert_called_once()
        mock_publisher.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_publisher_always_closed(self, config, mock_publisher, mock_vllm_client, execution_request):
        """Test that publisher is always closed, even on errors."""
        # Arrange
        mock_publisher.connect = AsyncMock(side_effect=RuntimeError("NATS error"))
        
        use_case = ExecuteAgentTask(
            config=config,
            publisher=mock_publisher,
            vllm_client=mock_vllm_client,
            vllm_agent=None,
        )
        
        # Act
        result = await use_case.execute(execution_request)
        
        # Assert
        assert result["status"] == "failed"
        
        # Verify publisher.close was called even though connect failed
        mock_publisher.close.assert_called_once()

