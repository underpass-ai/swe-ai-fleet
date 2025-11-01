"""Unit tests for ProcessCommand value object."""

import pytest
from pathlib import Path

from core.agents_and_tools.tools.domain.process_command import ProcessCommand


# =============================================================================
# Constructor Validation Tests (Fail-Fast)
# =============================================================================

class TestProcessCommandConstructorValidation:
    """Test fail-fast validation in ProcessCommand constructor."""

    def test_rejects_empty_command(self):
        """Should reject empty command (fail-fast)."""
        with pytest.raises(ValueError, match="command is required and cannot be empty"):
            ProcessCommand(command=[])

    def test_rejects_non_list_command(self):
        """Should reject non-list command (fail-fast)."""
        with pytest.raises(ValueError, match="command must be a list of strings"):
            ProcessCommand(command="ls -la")  # type: ignore

    def test_rejects_command_with_non_string_args(self):
        """Should reject command with non-string arguments (fail-fast)."""
        with pytest.raises(ValueError, match="all command arguments must be strings"):
            ProcessCommand(command=["ls", "-la", 123])  # type: ignore

    def test_rejects_non_integer_timeout(self):
        """Should reject non-integer timeout (fail-fast)."""
        with pytest.raises(ValueError, match="timeout must be an integer"):
            ProcessCommand(command=["ls"], timeout=3.5)  # type: ignore

    def test_rejects_zero_timeout(self):
        """Should reject zero timeout (fail-fast)."""
        with pytest.raises(ValueError, match="timeout must be positive"):
            ProcessCommand(command=["ls"], timeout=0)

    def test_rejects_negative_timeout(self):
        """Should reject negative timeout (fail-fast)."""
        with pytest.raises(ValueError, match="timeout must be positive"):
            ProcessCommand(command=["ls"], timeout=-5)

    def test_rejects_non_boolean_capture_output(self):
        """Should reject non-boolean capture_output (fail-fast)."""
        with pytest.raises(ValueError, match="capture_output must be a boolean"):
            ProcessCommand(command=["ls"], capture_output="yes")  # type: ignore

    def test_rejects_non_boolean_text_mode(self):
        """Should reject non-boolean text_mode (fail-fast)."""
        with pytest.raises(ValueError, match="text_mode must be a boolean"):
            ProcessCommand(command=["ls"], text_mode=1)  # type: ignore

    def test_rejects_non_boolean_check_returncode(self):
        """Should reject non-boolean check_returncode (fail-fast)."""
        with pytest.raises(ValueError, match="check_returncode must be a boolean"):
            ProcessCommand(command=["ls"], check_returncode="true")  # type: ignore


# =============================================================================
# Happy Path Tests
# =============================================================================

class TestProcessCommandHappyPath:
    """Test valid ProcessCommand creation and behavior."""

    def test_creates_simple_command(self):
        """Should create simple command with defaults."""
        cmd = ProcessCommand(command=["ls", "-la"])

        assert cmd.command == ["ls", "-la"]
        assert cmd.working_directory is None
        assert cmd.timeout == 30
        assert cmd.capture_output is True
        assert cmd.text_mode is True
        assert cmd.check_returncode is False

    def test_creates_command_with_working_directory(self):
        """Should create command with working directory."""
        cmd = ProcessCommand(
            command=["git", "status"],
            working_directory="/workspace"
        )

        assert cmd.working_directory == "/workspace"
        assert cmd.has_working_directory() is True

    def test_creates_command_with_path_working_directory(self):
        """Should accept Path as working directory."""
        cmd = ProcessCommand(
            command=["ls"],
            working_directory=Path("/tmp")
        )

        assert cmd.working_directory == Path("/tmp")

    def test_creates_command_with_custom_timeout(self):
        """Should create command with custom timeout."""
        cmd = ProcessCommand(
            command=["sleep", "10"],
            timeout=15
        )

        assert cmd.timeout == 15

    def test_creates_command_without_capture(self):
        """Should create command without output capture."""
        cmd = ProcessCommand(
            command=["echo", "hello"],
            capture_output=False
        )

        assert cmd.capture_output is False
        assert cmd.should_capture_output() is False

    def test_creates_command_with_check_returncode(self):
        """Should create command that checks returncode."""
        cmd = ProcessCommand(
            command=["docker", "version"],
            check_returncode=True
        )

        assert cmd.check_returncode is True
        assert cmd.should_check_returncode() is True

    def test_is_immutable(self):
        """Should be immutable (frozen dataclass)."""
        cmd = ProcessCommand(command=["ls"])

        with pytest.raises(Exception):  # FrozenInstanceError
            cmd.command = ["pwd"]  # type: ignore


# =============================================================================
# Business Logic Tests
# =============================================================================

class TestProcessCommandBusinessLogic:
    """Test ProcessCommand business methods."""

    def test_get_program_returns_first_element(self):
        """Should return program name (first command element)."""
        cmd = ProcessCommand(command=["podman", "ps", "-a"])

        assert cmd.get_program() == "podman"

    def test_get_args_returns_remaining_elements(self):
        """Should return arguments (all except first)."""
        cmd = ProcessCommand(command=["docker", "run", "-d", "nginx"])

        assert cmd.get_args() == ["run", "-d", "nginx"]

    def test_get_args_returns_empty_for_single_command(self):
        """Should return empty list for command without args."""
        cmd = ProcessCommand(command=["ls"])

        assert cmd.get_args() == []

    def test_has_working_directory_returns_false_when_none(self):
        """Should return False when no working directory."""
        cmd = ProcessCommand(command=["ls"])

        assert cmd.has_working_directory() is False

    def test_has_working_directory_returns_true_when_set(self):
        """Should return True when working directory is set."""
        cmd = ProcessCommand(command=["ls"], working_directory="/tmp")

        assert cmd.has_working_directory() is True

    def test_should_capture_output_reflects_setting(self):
        """Should reflect capture_output setting."""
        cmd_capture = ProcessCommand(command=["ls"], capture_output=True)
        cmd_no_capture = ProcessCommand(command=["ls"], capture_output=False)

        assert cmd_capture.should_capture_output() is True
        assert cmd_no_capture.should_capture_output() is False

    def test_is_text_mode_reflects_setting(self):
        """Should reflect text_mode setting."""
        cmd_text = ProcessCommand(command=["ls"], text_mode=True)
        cmd_binary = ProcessCommand(command=["ls"], text_mode=False)

        assert cmd_text.is_text_mode() is True
        assert cmd_binary.is_text_mode() is False

    def test_should_check_returncode_reflects_setting(self):
        """Should reflect check_returncode setting."""
        cmd_check = ProcessCommand(command=["ls"], check_returncode=True)
        cmd_no_check = ProcessCommand(command=["ls"], check_returncode=False)

        assert cmd_check.should_check_returncode() is True
        assert cmd_no_check.should_check_returncode() is False


# =============================================================================
# Factory Method Tests
# =============================================================================

class TestProcessCommandFactoryMethods:
    """Test ProcessCommand factory methods."""

    def test_simple_creates_command_from_args(self):
        """Should create simple command from variadic args."""
        cmd = ProcessCommand.simple("ls", "-la", "/tmp")

        assert cmd.command == ["ls", "-la", "/tmp"]
        assert cmd.timeout == 30
        assert cmd.capture_output is True
        assert cmd.text_mode is True

    def test_simple_creates_single_arg_command(self):
        """Should create command with single argument."""
        cmd = ProcessCommand.simple("pwd")

        assert cmd.command == ["pwd"]

    def test_for_runtime_check_creates_version_check(self):
        """Should create runtime check command."""
        cmd = ProcessCommand.for_runtime_check("podman")

        assert cmd.command == ["podman", "version"]
        assert cmd.timeout == 5
        assert cmd.capture_output is True
        assert cmd.check_returncode is True

    def test_for_runtime_check_works_with_docker(self):
        """Should create docker runtime check."""
        cmd = ProcessCommand.for_runtime_check("docker")

        assert cmd.command == ["docker", "version"]

    def test_in_workspace_creates_workspace_command(self):
        """Should create command for workspace execution."""
        cmd = ProcessCommand.in_workspace(
            command=["git", "status"],
            workspace_path="/workspace",
            timeout=60
        )

        assert cmd.command == ["git", "status"]
        assert cmd.working_directory == "/workspace"
        assert cmd.timeout == 60
        assert cmd.capture_output is True
        assert cmd.check_returncode is False

    def test_in_workspace_accepts_path_object(self):
        """Should accept Path object for workspace."""
        cmd = ProcessCommand.in_workspace(
            command=["ls"],
            workspace_path=Path("/tmp")
        )

        assert cmd.working_directory == Path("/tmp")

    def test_in_workspace_uses_default_timeout(self):
        """Should use default timeout when not specified."""
        cmd = ProcessCommand.in_workspace(
            command=["ls"],
            workspace_path="/workspace"
        )

        assert cmd.timeout == 30


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestProcessCommandEdgeCases:
    """Test ProcessCommand edge cases."""

    def test_accepts_single_word_command(self):
        """Should accept command with single word."""
        cmd = ProcessCommand(command=["ls"])

        assert cmd.command == ["ls"]
        assert cmd.get_program() == "ls"
        assert cmd.get_args() == []

    def test_accepts_command_with_many_args(self):
        """Should accept command with many arguments."""
        cmd = ProcessCommand(command=[
            "docker", "run", "-d", "-p", "8080:80",
            "-v", "/data:/data", "nginx:latest"
        ])

        assert len(cmd.command) == 8
        assert cmd.get_program() == "docker"
        assert len(cmd.get_args()) == 7

    def test_accepts_very_long_timeout(self):
        """Should accept very long timeout."""
        cmd = ProcessCommand(command=["sleep", "1000"], timeout=3600)

        assert cmd.timeout == 3600

    def test_working_directory_can_be_relative(self):
        """Should accept relative working directory."""
        cmd = ProcessCommand(command=["ls"], working_directory=".")

        assert cmd.working_directory == "."
        assert cmd.has_working_directory() is True

