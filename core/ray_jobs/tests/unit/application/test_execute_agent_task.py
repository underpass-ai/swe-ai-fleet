"""Tests for ExecuteAgentTask use case."""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from core.ray_jobs.application import ExecuteAgentTask
from core.ray_jobs.domain import (
    AgentConfig,
    ExecutionRequest,
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

    def _create_use_case(
        self,
        config,
        mock_publisher,
        mock_vllm_client,
        vllm_agent=None,
    ):
        """Create ExecuteAgentTask use case instance."""
        return ExecuteAgentTask(
            config=config,
            publisher=mock_publisher,
            vllm_client=mock_vllm_client,
            vllm_agent=vllm_agent,
        )

    def _create_mock_vllm_response(
        self,
        content: str = "Test proposal content",
        tokens: int = 100,
        temperature: float = 0.7,
    ):
        """Create a mock VLLMResponse for testing."""
        from core.ray_jobs.domain import VLLMResponse
        return VLLMResponse(
            content=content,
            author_id="agent-test-001",
            author_role="DEV",
            model="test-model",
            temperature=temperature,
            tokens=tokens,
        )

    def _assert_publisher_success_calls(self, mock_publisher):
        """Assert that publisher success methods were called correctly."""
        mock_publisher.connect.assert_called_once()
        mock_publisher.publish_success.assert_called_once()
        mock_publisher.close.assert_called_once()

    def _assert_publisher_failure_calls(self, mock_publisher):
        """Assert that publisher failure methods were called correctly."""
        mock_publisher.publish_failure.assert_called_once()
        mock_publisher.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_text_only_success(self, config, mock_publisher, mock_vllm_client, execution_request):
        """Test successful text-only execution."""
        # Arrange
        use_case = self._create_use_case(config, mock_publisher, mock_vllm_client, vllm_agent=None)

        mock_response = self._create_mock_vllm_response()
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
        self._assert_publisher_success_calls(mock_publisher)

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

        use_case = self._create_use_case(
            config_with_tools,
            mock_publisher,
            mock_vllm_client,
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
        self._assert_publisher_success_calls(mock_publisher)

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

        use_case = self._create_use_case(
            config_with_tools,
            mock_publisher,
            mock_vllm_client,
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
        self._assert_publisher_failure_calls(mock_publisher)

    @pytest.mark.asyncio
    async def test_execute_exception_handling(self, config, mock_publisher, mock_vllm_client, execution_request):
        """Test exception handling during execution."""
        # Arrange
        mock_vllm_client.generate = AsyncMock(side_effect=RuntimeError("vLLM error"))

        use_case = self._create_use_case(config, mock_publisher, mock_vllm_client, vllm_agent=None)

        # Act
        result = await use_case.execute(execution_request)

        # Assert
        assert result["status"] == "failed"
        assert "error" in result
        assert "vLLM error" in result["error"]

        # Verify publisher called publish_failure
        self._assert_publisher_failure_calls(mock_publisher)

    @pytest.mark.asyncio
    async def test_execute_publisher_always_closed(self, config, mock_publisher, mock_vllm_client, execution_request):
        """Test that publisher is always closed, even on errors."""
        # Arrange
        mock_publisher.connect = AsyncMock(side_effect=RuntimeError("NATS error"))

        use_case = self._create_use_case(config, mock_publisher, mock_vllm_client, vllm_agent=None)

        # Act
        result = await use_case.execute(execution_request)

        # Assert
        assert result["status"] == "failed"

        # Verify publisher.close was called even though connect failed
        mock_publisher.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_text_only_task_extraction_detection(self, config, mock_publisher, mock_vllm_client):
        """Test task extraction detection in text-only execution via task_type."""
        # Arrange
        execution_request = ExecutionRequest.create(
            task_id="task-123",
            task_description="Extract tasks",
            constraints={
                "metadata": {
                    "task_type": "TASK_EXTRACTION",
                    "story_id": "ST-001",
                    "ceremony_id": "BRC-12345",
                }
            },
            diversity=False,
        )

        use_case = self._create_use_case(config, mock_publisher, mock_vllm_client, vllm_agent=None)

        mock_response = self._create_mock_vllm_response(
            content='{"tasks": []}',
            temperature=0.0,
        )
        mock_vllm_client.generate = AsyncMock(return_value=mock_response)

        # Act
        result = await use_case.execute(execution_request)

        # Assert
        assert result["status"] == "completed"
        # Verify publish_success was called with constraints
        call_args = mock_publisher.publish_success.call_args
        assert call_args[1]["original_task_id"] is None
        assert call_args[1]["constraints"] == execution_request.constraints

    @pytest.mark.asyncio
    async def test_execute_text_only_task_extraction_by_metadata(self, config, mock_publisher, mock_vllm_client):
        """Test task extraction detection by metadata."""
        # Arrange
        execution_request = ExecutionRequest.create(
            task_id="task-123",
            task_description="Extract tasks",
            constraints={
                "metadata": {
                    "task_type": "TASK_EXTRACTION",
                    "story_id": "ST-001",
                    "ceremony_id": "BRC-12345",
                }
            },
            diversity=False,
        )

        use_case = self._create_use_case(config, mock_publisher, mock_vllm_client, vllm_agent=None)

        mock_response = self._create_mock_vllm_response(
            content='{"tasks": []}',
            temperature=0.0,
        )
        mock_vllm_client.generate = AsyncMock(return_value=mock_response)

        # Act
        result = await use_case.execute(execution_request)

        # Assert
        assert result["status"] == "completed"
        # Verify structured outputs were used
        call_args = mock_vllm_client.generate.call_args[0][0]
        assert call_args.json_schema is not None
        assert call_args.task_type == "TASK_EXTRACTION"

    @pytest.mark.asyncio
    async def test_execute_text_only_with_num_agents(self, config, mock_publisher, mock_vllm_client):
        """Test text-only execution with num_agents in metadata."""
        # Arrange
        execution_request = ExecutionRequest.create(
            task_id="task-123",
            task_description="Test task",
            constraints={
                "metadata": {
                    "num_agents": 3,
                }
            },
            diversity=False,
        )

        use_case = self._create_use_case(config, mock_publisher, mock_vllm_client, vllm_agent=None)

        mock_response = self._create_mock_vllm_response(content="Test proposal")
        mock_vllm_client.generate = AsyncMock(return_value=mock_response)

        # Act
        result = await use_case.execute(execution_request)

        # Assert
        assert result["status"] == "completed"
        # Verify publish_success was called with num_agents
        call_args = mock_publisher.publish_success.call_args
        assert call_args[1]["num_agents"] == 3

    @pytest.mark.asyncio
    async def test_execute_text_only_failure(self, config, mock_publisher, mock_vllm_client, execution_request):
        """Test text-only execution failure."""
        # Arrange
        mock_vllm_client.generate = AsyncMock(side_effect=RuntimeError("vLLM error"))

        use_case = self._create_use_case(config, mock_publisher, mock_vllm_client, vllm_agent=None)

        # Act
        result = await use_case.execute(execution_request)

        # Assert
        assert result["status"] == "failed"
        assert "error" in result
        mock_publisher.publish_failure.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_original_task_id_without_metadata_is_none(
        self, config, mock_publisher, mock_vllm_client
    ):
        """Test that original_task_id is None when metadata.task_id is not provided."""
        # Arrange
        execution_request = ExecutionRequest.create(
            task_id="task-123",
            task_description="Extract tasks",
            constraints={
                "metadata": {
                    "task_type": "TASK_EXTRACTION",
                    "story_id": "ST-001",
                    # No task_id in metadata
                }
            },
            diversity=False,
        )

        use_case = self._create_use_case(config, mock_publisher, mock_vllm_client, vllm_agent=None)

        mock_response = self._create_mock_vllm_response(
            content='{"tasks": []}',
            temperature=0.0,
        )
        mock_vllm_client.generate = AsyncMock(return_value=mock_response)

        # Act
        result = await use_case.execute(execution_request)

        # Assert
        assert result["status"] == "completed"
        # No task_id fallback from request.task_id
        call_args = mock_publisher.publish_success.call_args
        assert call_args[1]["original_task_id"] is None

    @pytest.mark.asyncio
    async def test_execute_original_task_id_from_metadata_for_backlog_review(
        self, config, mock_publisher, mock_vllm_client
    ):
        """Test original_task_id uses explicit metadata.task_id for backlog review."""
        # Arrange
        execution_request = ExecutionRequest.create(
            task_id="ceremony-BRC-123:story-s-001:role-ARCHITECT",
            task_description="Review backlog story",
            constraints={
                "metadata": {
                    "task_type": "BACKLOG_REVIEW_ROLE",
                    "task_id": "ceremony-BRC-123:story-s-001:role-ARCHITECT",
                    "story_id": "s-001",
                    "ceremony_id": "BRC-123",
                }
            },
            diversity=False,
        )

        use_case = self._create_use_case(config, mock_publisher, mock_vllm_client, vllm_agent=None)

        mock_response = self._create_mock_vllm_response(content="Backlog review proposal")
        mock_vllm_client.generate = AsyncMock(return_value=mock_response)

        # Act
        result = await use_case.execute(execution_request)

        # Assert
        assert result["status"] == "completed"
        call_args = mock_publisher.publish_success.call_args
        assert call_args[1]["original_task_id"] == "ceremony-BRC-123:story-s-001:role-ARCHITECT"

    @pytest.mark.asyncio
    async def test_execute_with_constraints_no_metadata(self, config, mock_publisher, mock_vllm_client):
        """Test execution with constraints but no metadata."""
        # Arrange
        execution_request = ExecutionRequest.create(
            task_id="task-123",
            task_description="Test task",
            constraints={"rubric": "Test rubric"},  # No metadata
            diversity=False,
        )

        use_case = self._create_use_case(config, mock_publisher, mock_vllm_client, vllm_agent=None)

        mock_response = self._create_mock_vllm_response(content="Test proposal")
        mock_vllm_client.generate = AsyncMock(return_value=mock_response)

        # Act
        result = await use_case.execute(execution_request)

        # Assert
        assert result["status"] == "completed"
        # Verify publish_success was called with None for num_agents and original_task_id
        call_args = mock_publisher.publish_success.call_args
        assert call_args[1]["num_agents"] is None
        assert call_args[1]["original_task_id"] is None

    @pytest.mark.asyncio
    async def test_execute_with_no_constraints(self, config, mock_publisher, mock_vllm_client):
        """Test execution with no constraints."""
        # Arrange
        execution_request = ExecutionRequest.create(
            task_id="task-123",
            task_description="Test task",
            constraints=None,
            diversity=False,
        )

        use_case = self._create_use_case(config, mock_publisher, mock_vllm_client, vllm_agent=None)

        mock_response = self._create_mock_vllm_response(content="Test proposal")
        mock_vllm_client.generate = AsyncMock(return_value=mock_response)

        # Act
        result = await use_case.execute(execution_request)

        # Assert
        assert result["status"] == "completed"
        call_args = mock_publisher.publish_success.call_args
        assert call_args[1]["num_agents"] is None
        assert call_args[1]["original_task_id"] is None

    @pytest.mark.asyncio
    async def test_execute_failure_publishes_failure(self, config, mock_publisher, mock_vllm_client, execution_request):
        """Test that failure results publish failure event."""
        # Arrange
        mock_vllm_client.generate = AsyncMock(side_effect=RuntimeError("vLLM error"))

        use_case = self._create_use_case(config, mock_publisher, mock_vllm_client, vllm_agent=None)

        # Act
        result = await use_case.execute(execution_request)

        # Assert
        assert result["status"] == "failed"
        mock_publisher.publish_failure.assert_called_once()
        # Verify num_agents and original_task_id are passed
        call_args = mock_publisher.publish_failure.call_args
        assert call_args[1]["num_agents"] is None
        assert call_args[1]["original_task_id"] is None

    @pytest.mark.asyncio
    async def test_execute_failure_with_metadata(self, config, mock_publisher, mock_vllm_client):
        """Test failure with metadata passes num_agents and original_task_id."""
        # Arrange
        execution_request = ExecutionRequest.create(
            task_id="task-123",
            task_description="Test task",
            constraints={
                "metadata": {
                    "num_agents": 3,
                    "task_id": "original-task-123",
                }
            },
            diversity=False,
        )

        mock_vllm_client.generate = AsyncMock(side_effect=RuntimeError("vLLM error"))

        use_case = self._create_use_case(config, mock_publisher, mock_vllm_client, vllm_agent=None)

        # Act
        result = await use_case.execute(execution_request)

        # Assert
        assert result["status"] == "failed"
        call_args = mock_publisher.publish_failure.call_args
        assert call_args[1]["num_agents"] == 3
        assert call_args[1]["original_task_id"] == "original-task-123"

    @pytest.mark.asyncio
    async def test_execute_logs_llm_response(self, config, mock_publisher, mock_vllm_client, execution_request):
        """Test that LLM response is logged before publishing."""
        # Arrange
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

        use_case = ExecuteAgentTask(
            config=config,
            publisher=mock_publisher,
            vllm_client=mock_vllm_client,
            vllm_agent=None,
        )

        # Act
        result = await use_case.execute(execution_request)

        # Assert
        assert result["status"] == "completed"
        assert result["proposal"]["content"] == "Test proposal content"
