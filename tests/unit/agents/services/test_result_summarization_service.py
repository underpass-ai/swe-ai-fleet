"""Unit tests for ResultSummarizationApplicationService."""

from unittest.mock import Mock

import pytest
from core.agents_and_tools.agents.application.services.result_summarization_service import (
    ResultSummarizationApplicationService,
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

class TestResultSummarizationServiceConstructor:
    """Test constructor fail-fast validation."""

    def test_rejects_missing_tool_execution_port(self):
        """Should raise ValueError if tool_execution_port is None."""
        with pytest.raises(ValueError, match="tool_execution_port is required"):
            ResultSummarizationApplicationService(tool_execution_port=None)

    def test_accepts_valid_tool_execution_port(self, mock_tool_execution_port):
        """Should create instance when tool_execution_port is provided."""
        service = ResultSummarizationApplicationService(
            tool_execution_port=mock_tool_execution_port
        )

        assert service.tool_execution_port is mock_tool_execution_port


# =============================================================================
# Summarization Tests
# =============================================================================

class TestResultSummarizationService:
    """Test result summarization logic."""

    def test_summarize_delegates_to_tool(self, mock_tool_execution_port):
        """Should delegate to tool's summarize_result method."""
        # Arrange
        tool_mock = Mock()
        tool_mock.summarize_result.return_value = "Successfully listed 5 files"
        mock_tool_execution_port.get_tool_by_name.return_value = tool_mock

        service = ResultSummarizationApplicationService(
            tool_execution_port=mock_tool_execution_port
        )

        step = ExecutionStep(tool="files", operation="list_files", params={"path": "."})
        tool_result = Mock()

        # Act
        summary = service.summarize(step, tool_result, {"path": "."})

        # Assert
        assert summary == "Successfully listed 5 files"
        mock_tool_execution_port.get_tool_by_name.assert_called_once_with("files")
        tool_mock.summarize_result.assert_called_once_with("list_files", tool_result, {"path": "."})

    def test_summarize_uses_step_params_when_params_not_provided(self, mock_tool_execution_port):
        """Should use step.params when params argument is None."""
        # Arrange
        tool_mock = Mock()
        tool_mock.summarize_result.return_value = "File read successfully"
        mock_tool_execution_port.get_tool_by_name.return_value = tool_mock

        service = ResultSummarizationApplicationService(
            tool_execution_port=mock_tool_execution_port
        )

        step = ExecutionStep(tool="files", operation="read_file", params={"path": "test.py"})
        tool_result = Mock()

        # Act
        summary = service.summarize(step, tool_result, params=None)

        # Assert
        assert summary == "File read successfully"
        tool_mock.summarize_result.assert_called_once_with("read_file", tool_result, {"path": "test.py"})

    def test_summarize_handles_missing_tool(self, mock_tool_execution_port):
        """Should return default message when tool is not found."""
        # Arrange
        mock_tool_execution_port.get_tool_by_name.return_value = None

        service = ResultSummarizationApplicationService(
            tool_execution_port=mock_tool_execution_port
        )

        step = ExecutionStep(tool="unknown", operation="unknown_op", params={})
        tool_result = Mock()

        # Act
        summary = service.summarize(step, tool_result, {})

        # Assert
        assert summary == "Operation completed"
        mock_tool_execution_port.get_tool_by_name.assert_called_once_with("unknown")

    def test_summarize_handles_step_with_no_params(self, mock_tool_execution_port):
        """Should handle step with no params gracefully."""
        # Arrange
        tool_mock = Mock()
        tool_mock.summarize_result.return_value = "Operation completed"
        mock_tool_execution_port.get_tool_by_name.return_value = tool_mock

        service = ResultSummarizationApplicationService(
            tool_execution_port=mock_tool_execution_port
        )

        step = ExecutionStep(tool="git", operation="status", params=None)
        tool_result = Mock()

        # Act
        summary = service.summarize(step, tool_result, params=None)

        # Assert
        assert summary == "Operation completed"
        tool_mock.summarize_result.assert_called_once_with("status", tool_result, {})

    def test_summarize_with_explicit_params_overrides_step_params(self, mock_tool_execution_port):
        """Should use explicit params argument even if step has params."""
        # Arrange
        tool_mock = Mock()
        tool_mock.summarize_result.return_value = "Custom summary"
        mock_tool_execution_port.get_tool_by_name.return_value = tool_mock

        service = ResultSummarizationApplicationService(
            tool_execution_port=mock_tool_execution_port
        )

        step = ExecutionStep(tool="files", operation="write", params={"path": "old.txt"})
        tool_result = Mock()
        explicit_params = {"path": "new.txt", "content": "new content"}

        # Act
        summary = service.summarize(step, tool_result, explicit_params)

        # Assert
        assert summary == "Custom summary"
        tool_mock.summarize_result.assert_called_once_with("write", tool_result, explicit_params)

