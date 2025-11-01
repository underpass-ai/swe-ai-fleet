"""Unit tests for StepExecutionApplicationService."""

from unittest.mock import Mock

import pytest
from core.agents_and_tools.agents.application.dtos.step_execution_dto import StepExecutionDTO
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
            StepExecutionApplicationService(tool_execution_port=None)

    def test_accepts_valid_tool_execution_port(self, mock_tool_execution_port):
        """Should create instance when tool_execution_port is provided."""
        service = StepExecutionApplicationService(
            tool_execution_port=mock_tool_execution_port
        )

        assert service.tool_execution_port is mock_tool_execution_port


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
            tool_execution_port=mock_tool_execution_port
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
            tool_execution_port=mock_tool_execution_port
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
            tool_execution_port=mock_tool_execution_port
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
            tool_execution_port=mock_tool_execution_port
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
            tool_execution_port=mock_tool_execution_port
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
            tool_execution_port=mock_tool_execution_port
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
            tool_execution_port=mock_tool_execution_port
        )

        step = ExecutionStep(tool="database", operation="query", params={})

        # Act
        result = await service.execute(step, enable_write=True)

        # Assert
        assert result.success is False
        assert result.result is None
        assert result.error == "Unexpected error"

