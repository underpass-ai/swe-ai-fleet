"""Tests for kubectl tool."""

from unittest.mock import Mock, patch

import pytest
from core.agents_and_tools.tools.kubectl_tool import kubectl_apply_dry_run


class TestKubectlTool:
    """Test cases for kubectl tool."""

    @patch('core.agents_and_tools.tools.kubectl_tool.subprocess.run')
    def test_kubectl_apply_dry_run_success(self, mock_run):
        """Test kubectl_apply_dry_run with successful execution."""
        mock_proc = Mock()
        mock_proc.returncode = 0
        mock_proc.stdout = "deployment.apps/test-deployment created (dry run)"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        result = kubectl_apply_dry_run("/path/to/manifest.yaml")

        assert result == (True, "deployment.apps/test-deployment created (dry run)")
        mock_run.assert_called_once_with(
            ["kubectl", "apply", "--dry-run=server", "-f", "/path/to/manifest.yaml"],
            capture_output=True,
            text=True
        )

    @patch('core.agents_and_tools.tools.kubectl_tool.subprocess.run')
    def test_kubectl_apply_dry_run_failure(self, mock_run):
        """Test kubectl_apply_dry_run with failed execution."""
        mock_proc = Mock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = "Error: invalid manifest syntax"
        mock_run.return_value = mock_proc

        result = kubectl_apply_dry_run("/path/to/invalid-manifest.yaml")

        assert result == (False, "Error: invalid manifest syntax")
        mock_run.assert_called_once_with(
            ["kubectl", "apply", "--dry-run=server", "-f", "/path/to/invalid-manifest.yaml"],
            capture_output=True,
            text=True
        )

    @patch('core.agents_and_tools.tools.kubectl_tool.subprocess.run')
    def test_kubectl_apply_dry_run_with_warnings(self, mock_run):
        """Test kubectl_apply_dry_run with warnings in output."""
        mock_proc = Mock()
        mock_proc.returncode = 0
        mock_proc.stdout = "deployment.apps/test-deployment created (dry run)"
        mock_proc.stderr = "Warning: deprecated API version"
        mock_run.return_value = mock_proc

        result = kubectl_apply_dry_run("/path/to/manifest.yaml")

        assert result == (True, "deployment.apps/test-deployment created (dry run)Warning: deprecated API version")
        mock_run.assert_called_once_with(
            ["kubectl", "apply", "--dry-run=server", "-f", "/path/to/manifest.yaml"],
            capture_output=True,
            text=True
        )

    @patch('core.agents_and_tools.tools.kubectl_tool.subprocess.run')
    def test_kubectl_apply_dry_run_empty_manifest_path(self, mock_run):
        """Test kubectl_apply_dry_run with empty manifest path."""
        mock_proc = Mock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = "Error: manifest path is required"
        mock_run.return_value = mock_proc

        result = kubectl_apply_dry_run("")

        assert result == (False, "Error: manifest path is required")
        mock_run.assert_called_once_with(
            ["kubectl", "apply", "--dry-run=server", "-f", ""],
            capture_output=True,
            text=True
        )

    @patch('core.agents_and_tools.tools.kubectl_tool.subprocess.run')
    def test_kubectl_apply_dry_run_nonexistent_manifest(self, mock_run):
        """Test kubectl_apply_dry_run with nonexistent manifest file."""
        mock_proc = Mock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = "Error: manifest file not found"
        mock_run.return_value = mock_proc

        result = kubectl_apply_dry_run("/nonexistent/manifest.yaml")

        assert result == (False, "Error: manifest file not found")
        mock_run.assert_called_once_with(
            ["kubectl", "apply", "--dry-run=server", "-f", "/nonexistent/manifest.yaml"],
            capture_output=True,
            text=True
        )

    @patch('core.agents_and_tools.tools.kubectl_tool.subprocess.run')
    def test_kubectl_apply_dry_run_rbac_error(self, mock_run):
        """Test kubectl_apply_dry_run with RBAC error."""
        mock_proc = Mock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = "Error: forbidden: user does not have permission"
        mock_run.return_value = mock_proc

        result = kubectl_apply_dry_run("/path/to/manifest.yaml")

        assert result == (False, "Error: forbidden: user does not have permission")
        mock_run.assert_called_once_with(
            ["kubectl", "apply", "--dry-run=server", "-f", "/path/to/manifest.yaml"],
            capture_output=True,
            text=True
        )

    @patch('core.agents_and_tools.tools.kubectl_tool.subprocess.run')
    def test_kubectl_apply_dry_run_subprocess_exception(self, mock_run):
        """Test kubectl_apply_dry_run when subprocess raises an exception."""
        mock_run.side_effect = FileNotFoundError("kubectl command not found")

        with pytest.raises(FileNotFoundError):
            kubectl_apply_dry_run("/path/to/manifest.yaml")

    def test_kubectl_apply_dry_run_return_type(self):
        """Test that kubectl_apply_dry_run returns correct types."""
        with patch('core.agents_and_tools.tools.kubectl_tool.subprocess.run') as mock_run:
            mock_proc = Mock()
            mock_proc.returncode = 0
            mock_proc.stdout = "Success"
            mock_proc.stderr = ""
            mock_run.return_value = mock_proc

            result = kubectl_apply_dry_run("/path/to/manifest.yaml")

            assert isinstance(result, tuple)
            assert len(result) == 2
            assert isinstance(result[0], bool)
            assert isinstance(result[1], str)

    @patch('core.agents_and_tools.tools.kubectl_tool.subprocess.run')
    def test_kubectl_apply_dry_run_multiple_manifests(self, mock_run):
        """Test kubectl_apply_dry_run with multiple manifest files."""
        mock_proc = Mock()
        mock_proc.returncode = 0
        mock_proc.stdout = "deployment.apps/app created (dry run)\nservice/app-svc created (dry run)"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        result = kubectl_apply_dry_run("/path/to/multiple-manifests.yaml")

        assert result == (True, "deployment.apps/app created (dry run)\nservice/app-svc created (dry run)")
        mock_run.assert_called_once_with(
            ["kubectl", "apply", "--dry-run=server", "-f", "/path/to/multiple-manifests.yaml"],
            capture_output=True,
            text=True
        )
