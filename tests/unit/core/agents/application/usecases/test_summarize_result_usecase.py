"""Unit tests for SummarizeResultUseCase."""

from unittest.mock import Mock

import pytest

from core.agents_and_tools.agents.application.usecases.summarize_result_usecase import (
    SummarizeResultUseCase,
)
from core.agents_and_tools.common.domain.ports.tool_execution_port import ToolExecutionPort


class TestSummarizeResultUseCase:
    """Unit tests for SummarizeResultUseCase."""

    def test_summarize_result_happy_path(self):
        """Test result summarization with successful tool execution."""
        # Arrange
        mock_tool = Mock()
        mock_tool.summarize_result.return_value = "File written successfully: src/main.py"

        mock_tool_execution_port = Mock(spec=ToolExecutionPort)
        mock_tool_execution_port.get_tool_by_name.return_value = mock_tool

        use_case = SummarizeResultUseCase(
            tool_execution_port=mock_tool_execution_port,
        )

        mock_result = Mock()

        # Act
        summary = use_case.execute(
            tool_name="files",
            operation="write_file",
            tool_result=mock_result,
            params={"path": "src/main.py", "content": "print('hello')"},
        )

        # Assert
        assert isinstance(summary, str)
        assert summary == "File written successfully: src/main.py"
        mock_tool.summarize_result.assert_called_once()

    def test_summarize_result_no_tool_found(self):
        """Test result summarization when tool is not found."""
        # Arrange
        mock_tool_execution_port = Mock(spec=ToolExecutionPort)
        mock_tool_execution_port.get_tool_by_name.return_value = None

        use_case = SummarizeResultUseCase(
            tool_execution_port=mock_tool_execution_port,
        )

        mock_result = Mock()

        # Act
        summary = use_case.execute(
            tool_name="unknown_tool",
            operation="unknown_operation",
            tool_result=mock_result,
            params={},
        )

        # Assert
        assert isinstance(summary, str)
        assert summary == "Operation completed"

    def test_summarize_result_tool_execution_port_required(self):
        """Test that tool_execution_port is required (fail-fast)."""
        # Act & Assert
        with pytest.raises(ValueError, match="tool_execution_port is required"):
            SummarizeResultUseCase(
                tool_execution_port=None,
            )

