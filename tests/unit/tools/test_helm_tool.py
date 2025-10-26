"""Tests for Helm tool."""

import pytest
from unittest.mock import patch, Mock
from core.agents_and_tools.tools.helm_tool import helm_lint


class TestHelmTool:
    """Test cases for Helm tool."""

    @patch('core.agents_and_tools.tools.helm_tool.subprocess.run')
    def test_helm_lint_success(self, mock_run):
        """Test helm_lint with successful execution."""
        mock_proc = Mock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Chart validation passed"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        result = helm_lint("/path/to/chart")

        assert result == (True, "Chart validation passed")
        mock_run.assert_called_once_with(
            ["helm", "lint", "/path/to/chart"],
            capture_output=True,
            text=True
        )

    @patch('core.agents_and_tools.tools.helm_tool.subprocess.run')
    def test_helm_lint_failure(self, mock_run):
        """Test helm_lint with failed execution."""
        mock_proc = Mock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = "Error: Chart validation failed"
        mock_run.return_value = mock_proc

        result = helm_lint("/path/to/invalid-chart")

        assert result == (False, "Error: Chart validation failed")
        mock_run.assert_called_once_with(
            ["helm", "lint", "/path/to/invalid-chart"],
            capture_output=True,
            text=True
        )

    @patch('core.agents_and_tools.tools.helm_tool.subprocess.run')
    def test_helm_lint_with_warnings(self, mock_run):
        """Test helm_lint with warnings in output."""
        mock_proc = Mock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Chart validation passed"
        mock_proc.stderr = "Warning: Deprecated API version"
        mock_run.return_value = mock_proc

        result = helm_lint("/path/to/chart")

        assert result == (True, "Chart validation passedWarning: Deprecated API version")
        mock_run.assert_called_once_with(
            ["helm", "lint", "/path/to/chart"],
            capture_output=True,
            text=True
        )

    @patch('core.agents_and_tools.tools.helm_tool.subprocess.run')
    def test_helm_lint_empty_chart_dir(self, mock_run):
        """Test helm_lint with empty chart directory."""
        mock_proc = Mock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = "Error: Chart directory is empty"
        mock_run.return_value = mock_proc

        result = helm_lint("")

        assert result == (False, "Error: Chart directory is empty")
        mock_run.assert_called_once_with(
            ["helm", "lint", ""],
            capture_output=True,
            text=True
        )

    @patch('core.agents_and_tools.tools.helm_tool.subprocess.run')
    def test_helm_lint_nonexistent_chart(self, mock_run):
        """Test helm_lint with nonexistent chart directory."""
        mock_proc = Mock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = "Error: Chart directory not found"
        mock_run.return_value = mock_proc

        result = helm_lint("/nonexistent/path")

        assert result == (False, "Error: Chart directory not found")
        mock_run.assert_called_once_with(
            ["helm", "lint", "/nonexistent/path"],
            capture_output=True,
            text=True
        )

    @patch('core.agents_and_tools.tools.helm_tool.subprocess.run')
    def test_helm_lint_subprocess_exception(self, mock_run):
        """Test helm_lint when subprocess raises an exception."""
        mock_run.side_effect = FileNotFoundError("helm command not found")

        with pytest.raises(FileNotFoundError):
            helm_lint("/path/to/chart")

    def test_helm_lint_return_type(self):
        """Test that helm_lint returns correct types."""
        with patch('core.agents_and_tools.tools.helm_tool.subprocess.run') as mock_run:
            mock_proc = Mock()
            mock_proc.returncode = 0
            mock_proc.stdout = "Success"
            mock_proc.stderr = ""
            mock_run.return_value = mock_proc

            result = helm_lint("/path/to/chart")

            assert isinstance(result, tuple)
            assert len(result) == 2
            assert isinstance(result[0], bool)
            assert isinstance(result[1], str)
