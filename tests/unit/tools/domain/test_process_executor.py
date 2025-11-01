"""Unit tests for process executor."""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from core.agents_and_tools.tools.domain.process_command import ProcessCommand
from core.agents_and_tools.tools.domain.process_executor import execute_process
from core.agents_and_tools.tools.domain.process_result import ProcessResult


# =============================================================================
# Happy Path Tests
# =============================================================================

class TestProcessExecutorHappyPath:
    """Test successful process execution scenarios."""

    @patch("subprocess.run")
    def test_executes_simple_command(self, mock_run):
        """Should execute simple command and return ProcessResult."""
        # Mock subprocess result
        mock_result = Mock()
        mock_result.stdout = "output"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Execute
        cmd = ProcessCommand.simple("ls", "-la")
        result = execute_process(cmd)

        # Verify subprocess.run was called correctly
        mock_run.assert_called_once_with(
            ["ls", "-la"],
            cwd=None,
            timeout=30,
            capture_output=True,
            text=True,
            check=False,
        )

        # Verify result entity
        assert isinstance(result, ProcessResult)
        assert result.stdout == "output"
        assert result.stderr == ""
        assert result.returncode == 0
        assert result.is_success() is True

    @patch("subprocess.run")
    def test_executes_command_with_working_directory(self, mock_run):
        """Should execute command in specified working directory."""
        mock_result = Mock()
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        cmd = ProcessCommand.in_workspace(
            command=["git", "status"],
            workspace_path="/workspace"
        )
        result = execute_process(cmd)

        # Verify cwd was passed
        mock_run.assert_called_once()
        assert mock_run.call_args.kwargs["cwd"] == "/workspace"
        assert result.is_success() is True

    @patch("subprocess.run")
    def test_executes_command_with_path_working_directory(self, mock_run):
        """Should accept Path object for working directory."""
        mock_result = Mock()
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        cmd = ProcessCommand(
            command=["ls"],
            working_directory=Path("/tmp")
        )
        result = execute_process(cmd)

        # Verify Path was passed
        assert mock_run.call_args.kwargs["cwd"] == Path("/tmp")

    @patch("subprocess.run")
    def test_executes_command_with_custom_timeout(self, mock_run):
        """Should use custom timeout from command."""
        mock_result = Mock()
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        cmd = ProcessCommand(command=["sleep", "5"], timeout=60)
        result = execute_process(cmd)

        # Verify timeout was passed
        assert mock_run.call_args.kwargs["timeout"] == 60

    @patch("subprocess.run")
    def test_executes_without_output_capture(self, mock_run):
        """Should execute without capturing output if disabled."""
        mock_result = Mock()
        mock_result.stdout = None
        mock_result.stderr = None
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        cmd = ProcessCommand(
            command=["echo", "test"],
            capture_output=False
        )
        result = execute_process(cmd)

        # Verify capture_output=False was passed
        assert mock_run.call_args.kwargs["capture_output"] is False
        assert result.stdout == ""  # None converted to ""

    @patch("subprocess.run")
    def test_executes_in_binary_mode(self, mock_run):
        """Should execute in binary mode if text=False."""
        mock_result = Mock()
        mock_result.stdout = b""
        mock_result.stderr = b""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        cmd = ProcessCommand(
            command=["ls"],
            text_mode=False
        )
        result = execute_process(cmd)

        # Verify text=False was passed
        assert mock_run.call_args.kwargs["text"] is False

    @patch("subprocess.run")
    def test_returns_failed_result_without_raising(self, mock_run):
        """Should return failed result without raising by default."""
        mock_result = Mock()
        mock_result.stdout = ""
        mock_result.stderr = "error"
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        cmd = ProcessCommand.simple("false")
        result = execute_process(cmd)

        # Should not raise, just return failed result
        assert result.is_success() is False
        assert result.returncode == 1


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestProcessExecutorErrorHandling:
    """Test error handling scenarios."""

    @patch("subprocess.run")
    def test_raises_on_error_when_check_returncode_true(self, mock_run):
        """Should raise CalledProcessError when check_returncode=True."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=127,
            cmd=["nonexistent"],
            stderr="command not found"
        )

        cmd = ProcessCommand(
            command=["nonexistent"],
            check_returncode=True
        )

        with pytest.raises(subprocess.CalledProcessError):
            execute_process(cmd)

        # Verify check=True was passed
        assert mock_run.call_args.kwargs["check"] is True

    @patch("subprocess.run")
    def test_raises_on_error_when_override_true(self, mock_run):
        """Should raise when raise_on_error override is True."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["false"]
        )

        cmd = ProcessCommand.simple("false")  # check_returncode=False by default

        with pytest.raises(subprocess.CalledProcessError):
            execute_process(cmd, raise_on_error=True)

        # Verify check=True was passed (override)
        assert mock_run.call_args.kwargs["check"] is True

    @patch("subprocess.run")
    def test_does_not_raise_when_override_false(self, mock_run):
        """Should not raise when raise_on_error override is False."""
        mock_result = Mock()
        mock_result.stdout = ""
        mock_result.stderr = "error"
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        cmd = ProcessCommand(
            command=["false"],
            check_returncode=True  # Would normally raise
        )

        result = execute_process(cmd, raise_on_error=False)

        # Verify check=False was passed (override)
        assert mock_run.call_args.kwargs["check"] is False
        assert result.returncode == 1

    @patch("subprocess.run")
    def test_raises_timeout_expired(self, mock_run):
        """Should raise TimeoutExpired when command times out."""
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["sleep", "100"],
            timeout=1
        )

        cmd = ProcessCommand(command=["sleep", "100"], timeout=1)

        with pytest.raises(subprocess.TimeoutExpired):
            execute_process(cmd)

    @patch("subprocess.run")
    def test_raises_file_not_found(self, mock_run):
        """Should raise FileNotFoundError when program not found."""
        mock_run.side_effect = FileNotFoundError("nonexistent: command not found")

        cmd = ProcessCommand.simple("nonexistent")

        with pytest.raises(FileNotFoundError):
            execute_process(cmd)


# =============================================================================
# Integration with ProcessCommand Tests
# =============================================================================

class TestProcessExecutorIntegration:
    """Test integration with ProcessCommand factory methods."""

    @patch("subprocess.run")
    def test_works_with_simple_factory(self, mock_run):
        """Should work with ProcessCommand.simple() factory."""
        mock_result = Mock()
        mock_result.stdout = "files"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        cmd = ProcessCommand.simple("ls", "-la", "/tmp")
        result = execute_process(cmd)

        mock_run.assert_called_once()
        assert mock_run.call_args.args[0] == ["ls", "-la", "/tmp"]
        assert result.is_success() is True

    @patch("subprocess.run")
    def test_works_with_runtime_check_factory(self, mock_run):
        """Should work with ProcessCommand.for_runtime_check() factory."""
        mock_result = Mock()
        mock_result.stdout = "Docker version 20.10"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        cmd = ProcessCommand.for_runtime_check("docker")
        result = execute_process(cmd)

        # Runtime check uses check=True by default
        assert mock_run.call_args.kwargs["check"] is True
        assert mock_run.call_args.kwargs["timeout"] == 5
        assert result.command == ["docker", "version"]

    @patch("subprocess.run")
    def test_works_with_in_workspace_factory(self, mock_run):
        """Should work with ProcessCommand.in_workspace() factory."""
        mock_result = Mock()
        mock_result.stdout = "On branch main"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        cmd = ProcessCommand.in_workspace(
            command=["git", "status"],
            workspace_path="/workspace",
            timeout=60
        )
        result = execute_process(cmd)

        assert mock_run.call_args.kwargs["cwd"] == "/workspace"
        assert mock_run.call_args.kwargs["timeout"] == 60
        assert mock_run.call_args.kwargs["check"] is False


# =============================================================================
# ProcessResult Entity Conversion Tests
# =============================================================================

class TestProcessResultConversion:
    """Test ProcessResult entity creation from subprocess results."""

    @patch("subprocess.run")
    def test_converts_subprocess_result_to_entity(self, mock_run):
        """Should correctly convert subprocess.CompletedProcess to ProcessResult."""
        mock_result = Mock()
        mock_result.stdout = "Standard output"
        mock_result.stderr = "Standard error"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        cmd = ProcessCommand.simple("test")
        result = execute_process(cmd)

        # Verify entity fields
        assert result.stdout == "Standard output"
        assert result.stderr == "Standard error"
        assert result.returncode == 0
        assert result.command == ["test"]

    @patch("subprocess.run")
    def test_handles_none_outputs(self, mock_run):
        """Should convert None outputs to empty strings."""
        mock_result = Mock()
        mock_result.stdout = None
        mock_result.stderr = None
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        cmd = ProcessCommand.simple("ls")
        result = execute_process(cmd)

        assert result.stdout == ""
        assert result.stderr == ""

    @patch("subprocess.run")
    def test_preserves_command_in_result(self, mock_run):
        """Should preserve original command in result entity."""
        mock_result = Mock()
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        cmd = ProcessCommand.simple("docker", "run", "-d", "nginx")
        result = execute_process(cmd)

        assert result.command == ["docker", "run", "-d", "nginx"]
        assert result.get_command_str() == "docker run -d nginx"


# =============================================================================
# Real-World Usage Pattern Tests
# =============================================================================

class TestRealWorldUsagePatterns:
    """Test common real-world usage patterns."""

    @patch("subprocess.run")
    def test_runtime_detection_pattern(self, mock_run):
        """Should support runtime detection pattern."""
        # First try podman - fails
        mock_run.side_effect = [
            subprocess.CalledProcessError(127, ["podman"]),
            # Second try docker - succeeds
            Mock(stdout="Docker version", stderr="", returncode=0)
        ]

        runtime = None
        for rt in ["podman", "docker"]:
            try:
                cmd = ProcessCommand.for_runtime_check(rt)
                result = execute_process(cmd, raise_on_error=True)
                if result.is_success():
                    runtime = rt
                    break
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue

        assert runtime == "docker"
        assert mock_run.call_count == 2

    @patch("subprocess.run")
    def test_workspace_command_execution_pattern(self, mock_run):
        """Should support workspace command execution pattern."""
        mock_result = Mock()
        mock_result.stdout = "BUILD SUCCESS"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        cmd = ProcessCommand.in_workspace(
            command=["make", "build"],
            workspace_path="/workspace/project",
            timeout=300
        )
        result = execute_process(cmd)

        assert result.is_success() is True
        assert "SUCCESS" in result.stdout
        assert mock_run.call_args.kwargs["cwd"] == "/workspace/project"

    @patch("subprocess.run")
    def test_error_handling_with_result_inspection(self, mock_run):
        """Should support error handling by inspecting result."""
        mock_result = Mock()
        mock_result.stdout = ""
        mock_result.stderr = "Permission denied"
        mock_result.returncode = 126
        mock_run.return_value = mock_result

        cmd = ProcessCommand.simple("restricted-command")
        result = execute_process(cmd)  # Don't raise

        # Inspect result for error handling
        if not result.is_success():
            if result.has_errors():
                error_msg = result.stderr
                assert "Permission denied" in error_msg

