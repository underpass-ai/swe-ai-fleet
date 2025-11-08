"""Unit tests for StepExecutionApplicationService."""

from unittest.mock import Mock

import pytest
from core.agents_and_tools.agents.application.services.step_execution_service import (
    StepExecutionApplicationService,
)
from core.agents_and_tools.agents.domain.entities import ExecutionStep
from core.agents_and_tools.common.domain.ports.tool_execution_port import ToolExecutionPort

# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_tool_execution_port():
    """Create mock ToolExecutionPort."""
    return Mock(spec=ToolExecutionPort)


# =============================================================================
# Constructor Validation Tests
# =============================================================================

class TestStepExecutionServiceConstructor:
    """Test constructor fail-fast validation."""

    def test_rejects_missing_tool_execution_port(self):
        """Should raise ValueError if tool_execution_port is None."""
        with pytest.raises(ValueError, match="tool_execution_port is required"):
            StepExecutionApplicationService(
                tool_execution_port=None,
                allowed_tools=frozenset({"files", "git"})
            )

    def test_rejects_empty_allowed_tools(self, mock_tool_execution_port):
        """Should raise ValueError if allowed_tools is empty."""
        with pytest.raises(ValueError, match="allowed_tools is required"):
            StepExecutionApplicationService(
                tool_execution_port=mock_tool_execution_port,
                allowed_tools=frozenset()
            )

    def test_accepts_valid_parameters(self, mock_tool_execution_port):
        """Should create instance when all parameters are provided."""
        allowed_tools = frozenset({"files", "git", "tests"})
        service = StepExecutionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            allowed_tools=allowed_tools
        )

        assert service.tool_execution_port is mock_tool_execution_port
        assert service.allowed_tools == allowed_tools


# =============================================================================
# Execution Tests
# =============================================================================

class TestStepExecutionService:
    """Test step execution logic."""

    @pytest.mark.asyncio
    async def test_execute_successful_step(self, mock_tool_execution_port):
        """Should execute step and return success DTO."""
        # Arrange
        result_mock = Mock()
        result_mock.success = True
        result_mock.error = None
        mock_tool_execution_port.execute_operation.return_value = result_mock

        service = StepExecutionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            allowed_tools=frozenset({"files", "git", "tests", "docker", "db", "http"}),  # All tools for tests
        )

        step = ExecutionStep(tool="files", operation="list_files", params={"path": "."})

        # Act
        result = await service.execute(step, enable_write=True)

        # Assert
        assert result.success is True
        assert result.result is result_mock
        assert result.error is None
        mock_tool_execution_port.execute_operation.assert_called_once_with(
            tool_name="files",
            operation="list_files",
            params={"path": "."},
            enable_write=True,
        )

    @pytest.mark.asyncio
    async def test_execute_failed_step_with_error_message(self, mock_tool_execution_port):
        """Should handle failed step with error message."""
        # Arrange
        result_mock = Mock()
        result_mock.success = False
        result_mock.error = "File not found"
        mock_tool_execution_port.execute_operation.return_value = result_mock

        service = StepExecutionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            allowed_tools=frozenset({"files", "git", "tests", "docker", "db", "http"}),  # All tools for tests
        )

        step = ExecutionStep(tool="files", operation="read_file", params={"path": "missing.txt"})

        # Act
        result = await service.execute(step, enable_write=False)

        # Assert
        assert result.success is False
        assert result.result is result_mock
        assert result.error == "File not found"

    @pytest.mark.asyncio
    async def test_execute_failed_step_without_error_message(self, mock_tool_execution_port):
        """Should default to 'Unknown error' when error message is missing."""
        # Arrange
        result_mock = Mock()
        result_mock.success = False
        result_mock.error = None
        mock_tool_execution_port.execute_operation.return_value = result_mock

        service = StepExecutionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            allowed_tools=frozenset({"files", "git", "tests", "docker", "db", "http"}),  # All tools for tests
        )

        step = ExecutionStep(tool="git", operation="commit", params={})

        # Act
        result = await service.execute(step, enable_write=True)

        # Assert
        assert result.success is False
        assert result.result is result_mock
        assert result.error == "Unknown error"

    @pytest.mark.asyncio
    async def test_execute_with_no_params(self, mock_tool_execution_port):
        """Should handle step with no params gracefully."""
        # Arrange
        result_mock = Mock()
        result_mock.success = True
        result_mock.error = None
        mock_tool_execution_port.execute_operation.return_value = result_mock

        service = StepExecutionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            allowed_tools=frozenset({"files", "git", "tests", "docker", "db", "http"}),  # All tools for tests
        )

        step = ExecutionStep(tool="git", operation="status", params=None)

        # Act
        result = await service.execute(step, enable_write=True)

        # Assert
        assert result.success is True
        mock_tool_execution_port.execute_operation.assert_called_once_with(
            tool_name="git",
            operation="status",
            params={},
            enable_write=True,
        )

    @pytest.mark.asyncio
    async def test_execute_with_write_disabled(self, mock_tool_execution_port):
        """Should respect enable_write parameter."""
        # Arrange
        result_mock = Mock()
        result_mock.success = True
        result_mock.error = None
        mock_tool_execution_port.execute_operation.return_value = result_mock

        service = StepExecutionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            allowed_tools=frozenset({"files", "git", "tests", "docker", "db", "http"}),  # All tools for tests
        )

        step = ExecutionStep(tool="files", operation="write_file", params={"path": "test.txt"})

        # Act
        result = await service.execute(step, enable_write=False)

        # Assert
        assert result.success is True
        mock_tool_execution_port.execute_operation.assert_called_once_with(
            tool_name="files",
            operation="write_file",
            params={"path": "test.txt"},
            enable_write=False,
        )

    @pytest.mark.asyncio
    async def test_execute_handles_value_error(self, mock_tool_execution_port):
        """Should catch ValueError and return failure DTO."""
        # Arrange
        mock_tool_execution_port.execute_operation.side_effect = ValueError("Invalid parameter")

        service = StepExecutionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            allowed_tools=frozenset({"files", "git", "tests", "docker", "db", "http"}),  # All tools for tests
        )

        step = ExecutionStep(tool="files", operation="read_file", params={"path": ""})

        # Act
        result = await service.execute(step, enable_write=True)

        # Assert
        assert result.success is False
        assert result.result is None
        assert result.error == "Invalid parameter"

    @pytest.mark.asyncio
    async def test_execute_handles_unexpected_exception(self, mock_tool_execution_port):
        """Should catch unexpected exceptions and return failure DTO."""
        # Arrange
        mock_tool_execution_port.execute_operation.side_effect = RuntimeError("Unexpected error")

        service = StepExecutionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            allowed_tools=frozenset({"files", "git", "tests", "docker", "db", "http"}),  # All tools for tests
        )

        step = ExecutionStep(tool="files", operation="invalid_operation", params={})

        # Act
        result = await service.execute(step, enable_write=True)

        # Assert
        assert result.success is False
        assert result.result is None
        assert result.error == "Unexpected error"

