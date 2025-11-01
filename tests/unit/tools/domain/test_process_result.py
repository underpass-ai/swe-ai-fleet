"""Unit tests for ProcessResult entity."""

import pytest
from unittest.mock import Mock

from core.agents_and_tools.tools.domain.process_result import ProcessResult


# =============================================================================
# Constructor Validation Tests (Fail-Fast)
# =============================================================================

class TestProcessResultConstructorValidation:
    """Test fail-fast validation in ProcessResult constructor."""

    def test_rejects_none_stdout(self):
        """Should reject None stdout (fail-fast)."""
        with pytest.raises(ValueError, match="stdout is required"):
            ProcessResult(
                stdout=None,  # type: ignore
                stderr="",
                returncode=0,
                command=["ls"]
            )

    def test_rejects_none_stderr(self):
        """Should reject None stderr (fail-fast)."""
        with pytest.raises(ValueError, match="stderr is required"):
            ProcessResult(
                stdout="",
                stderr=None,  # type: ignore
                returncode=0,
                command=["ls"]
            )

    def test_rejects_non_integer_returncode(self):
        """Should reject non-integer returncode (fail-fast)."""
        with pytest.raises(ValueError, match="returncode must be an integer"):
            ProcessResult(
                stdout="",
                stderr="",
                returncode="0",  # type: ignore
                command=["ls"]
            )

    def test_rejects_empty_command(self):
        """Should reject empty command (fail-fast)."""
        with pytest.raises(ValueError, match="command is required and cannot be empty"):
            ProcessResult(
                stdout="",
                stderr="",
                returncode=0,
                command=[]
            )

    def test_rejects_non_list_command(self):
        """Should reject non-list command (fail-fast)."""
        with pytest.raises(ValueError, match="command must be a list"):
            ProcessResult(
                stdout="",
                stderr="",
                returncode=0,
                command="ls -la"  # type: ignore
            )


# =============================================================================
# Happy Path Tests
# =============================================================================

class TestProcessResultHappyPath:
    """Test valid ProcessResult creation and behavior."""

    def test_creates_successful_result(self):
        """Should create successful result."""
        result = ProcessResult(
            stdout="total 123",
            stderr="",
            returncode=0,
            command=["ls", "-la"]
        )

        assert result.stdout == "total 123"
        assert result.stderr == ""
        assert result.returncode == 0
        assert result.command == ["ls", "-la"]

    def test_creates_failed_result(self):
        """Should create failed result."""
        result = ProcessResult(
            stdout="",
            stderr="Error: command not found",
            returncode=127,
            command=["nonexistent"]
        )

        assert result.returncode == 127
        assert result.is_success() is False

    def test_creates_result_with_both_outputs(self):
        """Should create result with both stdout and stderr."""
        result = ProcessResult(
            stdout="Processing...",
            stderr="Warning: deprecated option",
            returncode=0,
            command=["tool", "--old-flag"]
        )

        assert result.stdout == "Processing..."
        assert result.stderr == "Warning: deprecated option"

    def test_is_immutable(self):
        """Should be immutable (frozen dataclass)."""
        result = ProcessResult(
            stdout="output",
            stderr="",
            returncode=0,
            command=["ls"]
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            result.returncode = 1  # type: ignore


# =============================================================================
# Business Logic Tests
# =============================================================================

class TestProcessResultBusinessLogic:
    """Test ProcessResult business methods."""

    def test_is_success_returns_true_for_zero_exit(self):
        """Should return True when returncode is 0."""
        result = ProcessResult(
            stdout="success",
            stderr="",
            returncode=0,
            command=["ls"]
        )

        assert result.is_success() is True

    def test_is_success_returns_false_for_nonzero_exit(self):
        """Should return False when returncode is not 0."""
        result = ProcessResult(
            stdout="",
            stderr="error",
            returncode=1,
            command=["false"]
        )

        assert result.is_success() is False

    def test_has_output_returns_true_when_stdout_exists(self):
        """Should return True when stdout is non-empty."""
        result = ProcessResult(
            stdout="some output",
            stderr="",
            returncode=0,
            command=["echo", "test"]
        )

        assert result.has_output() is True

    def test_has_output_returns_false_when_stdout_empty(self):
        """Should return False when stdout is empty."""
        result = ProcessResult(
            stdout="",
            stderr="error",
            returncode=1,
            command=["ls"]
        )

        assert result.has_output() is False

    def test_has_output_returns_false_for_whitespace_only(self):
        """Should return False for whitespace-only stdout."""
        result = ProcessResult(
            stdout="   \n  \t  ",
            stderr="",
            returncode=0,
            command=["ls"]
        )

        assert result.has_output() is False

    def test_has_errors_returns_true_when_stderr_exists(self):
        """Should return True when stderr is non-empty."""
        result = ProcessResult(
            stdout="",
            stderr="error message",
            returncode=1,
            command=["false"]
        )

        assert result.has_errors() is True

    def test_has_errors_returns_false_when_stderr_empty(self):
        """Should return False when stderr is empty."""
        result = ProcessResult(
            stdout="output",
            stderr="",
            returncode=0,
            command=["echo", "test"]
        )

        assert result.has_errors() is False

    def test_has_errors_returns_false_for_whitespace_only(self):
        """Should return False for whitespace-only stderr."""
        result = ProcessResult(
            stdout="output",
            stderr="  \n  ",
            returncode=0,
            command=["ls"]
        )

        assert result.has_errors() is False

    def test_get_combined_output_includes_both(self):
        """Should combine stdout and stderr."""
        result = ProcessResult(
            stdout="Standard output",
            stderr="Standard error",
            returncode=0,
            command=["ls"]
        )

        combined = result.get_combined_output()

        assert "STDOUT:" in combined
        assert "Standard output" in combined
        assert "STDERR:" in combined
        assert "Standard error" in combined

    def test_get_combined_output_handles_stdout_only(self):
        """Should handle stdout-only output."""
        result = ProcessResult(
            stdout="Only stdout",
            stderr="",
            returncode=0,
            command=["echo", "test"]
        )

        combined = result.get_combined_output()

        assert "STDOUT:" in combined
        assert "Only stdout" in combined
        assert "STDERR:" not in combined

    def test_get_combined_output_handles_stderr_only(self):
        """Should handle stderr-only output."""
        result = ProcessResult(
            stdout="",
            stderr="Only stderr",
            returncode=1,
            command=["false"]
        )

        combined = result.get_combined_output()

        assert "STDERR:" in combined
        assert "Only stderr" in combined
        assert "STDOUT:" not in combined

    def test_get_combined_output_handles_no_output(self):
        """Should handle no output."""
        result = ProcessResult(
            stdout="",
            stderr="",
            returncode=0,
            command=["ls"]
        )

        combined = result.get_combined_output()

        assert combined == "No output"

    def test_get_command_str_formats_command(self):
        """Should format command as space-separated string."""
        result = ProcessResult(
            stdout="",
            stderr="",
            returncode=0,
            command=["docker", "run", "-d", "nginx"]
        )

        assert result.get_command_str() == "docker run -d nginx"

    def test_get_command_str_handles_single_word(self):
        """Should handle single-word command."""
        result = ProcessResult(
            stdout="",
            stderr="",
            returncode=0,
            command=["ls"]
        )

        assert result.get_command_str() == "ls"


# =============================================================================
# Factory Method Tests
# =============================================================================

class TestProcessResultFactoryMethods:
    """Test ProcessResult factory methods."""

    def test_from_subprocess_result_creates_entity(self):
        """Should create ProcessResult from subprocess.CompletedProcess."""
        # Mock subprocess.CompletedProcess
        subprocess_result = Mock()
        subprocess_result.stdout = "process output"
        subprocess_result.stderr = "process error"
        subprocess_result.returncode = 0

        result = ProcessResult.from_subprocess_result(
            subprocess_result,
            command=["ls", "-la"]
        )

        assert result.stdout == "process output"
        assert result.stderr == "process error"
        assert result.returncode == 0
        assert result.command == ["ls", "-la"]

    def test_from_subprocess_result_handles_none_stdout(self):
        """Should convert None stdout to empty string."""
        subprocess_result = Mock()
        subprocess_result.stdout = None
        subprocess_result.stderr = ""
        subprocess_result.returncode = 0

        result = ProcessResult.from_subprocess_result(
            subprocess_result,
            command=["ls"]
        )

        assert result.stdout == ""

    def test_from_subprocess_result_handles_none_stderr(self):
        """Should convert None stderr to empty string."""
        subprocess_result = Mock()
        subprocess_result.stdout = ""
        subprocess_result.stderr = None
        subprocess_result.returncode = 0

        result = ProcessResult.from_subprocess_result(
            subprocess_result,
            command=["ls"]
        )

        assert result.stderr == ""

    def test_from_subprocess_result_preserves_nonzero_returncode(self):
        """Should preserve non-zero returncodes."""
        subprocess_result = Mock()
        subprocess_result.stdout = ""
        subprocess_result.stderr = "error"
        subprocess_result.returncode = 127

        result = ProcessResult.from_subprocess_result(
            subprocess_result,
            command=["nonexistent"]
        )

        assert result.returncode == 127
        assert result.is_success() is False


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestProcessResultEdgeCases:
    """Test ProcessResult edge cases."""

    def test_accepts_empty_strings(self):
        """Should accept empty strings for stdout and stderr."""
        result = ProcessResult(
            stdout="",
            stderr="",
            returncode=0,
            command=["true"]
        )

        assert result.stdout == ""
        assert result.stderr == ""

    def test_accepts_negative_returncode(self):
        """Should accept negative returncode (signal termination)."""
        result = ProcessResult(
            stdout="",
            stderr="Killed",
            returncode=-9,  # SIGKILL
            command=["sleep", "1000"]
        )

        assert result.returncode == -9
        assert result.is_success() is False

    def test_accepts_large_returncode(self):
        """Should accept large returncode values."""
        result = ProcessResult(
            stdout="",
            stderr="",
            returncode=255,
            command=["exit", "255"]
        )

        assert result.returncode == 255

    def test_handles_multiline_output(self):
        """Should handle multiline output."""
        result = ProcessResult(
            stdout="Line 1\nLine 2\nLine 3",
            stderr="Warning 1\nWarning 2",
            returncode=0,
            command=["ls", "-la"]
        )

        assert "Line 1" in result.stdout
        assert "Line 2" in result.stdout
        assert "Warning 1" in result.stderr

    def test_handles_very_long_command(self):
        """Should handle command with many arguments."""
        long_command = ["docker", "run"] + [f"--env VAR{i}=value{i}" for i in range(20)]
        result = ProcessResult(
            stdout="",
            stderr="",
            returncode=0,
            command=long_command
        )

        assert len(result.command) == 22
        cmd_str = result.get_command_str()
        assert "VAR0=value0" in cmd_str
        assert "VAR19=value19" in cmd_str

