"""Process command value object."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProcessCommand:
    """
    Value object representing a command to execute in a subprocess.

    Following DDD principles:
    - Immutable (frozen=True)
    - Fail-fast validation in __post_init__
    - Self-contained business logic
    """

    command: list[str]
    working_directory: str | Path | None = None
    timeout: int = 30
    capture_output: bool = True
    text_mode: bool = True
    check_returncode: bool = False

    def __post_init__(self) -> None:
        """
        Validate value object invariants (fail-fast).

        Raises:
            ValueError: If any invariant is violated
        """
        if not self.command:
            raise ValueError("command is required and cannot be empty (fail-fast)")
        if not isinstance(self.command, list):
            raise ValueError("command must be a list of strings (fail-fast)")
        if not all(isinstance(arg, str) for arg in self.command):
            raise ValueError("all command arguments must be strings (fail-fast)")
        if not isinstance(self.timeout, int):
            raise ValueError("timeout must be an integer (fail-fast)")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive (fail-fast)")
        if not isinstance(self.capture_output, bool):
            raise ValueError("capture_output must be a boolean (fail-fast)")
        if not isinstance(self.text_mode, bool):
            raise ValueError("text_mode must be a boolean (fail-fast)")
        if not isinstance(self.check_returncode, bool):
            raise ValueError("check_returncode must be a boolean (fail-fast)")

    def get_program(self) -> str:
        """Get the program name (first element of command)."""
        return self.command[0]

    def get_args(self) -> list[str]:
        """Get command arguments (all elements except first)."""
        return self.command[1:]

    def has_working_directory(self) -> bool:
        """Check if working directory is specified."""
        return self.working_directory is not None

    def should_capture_output(self) -> bool:
        """Check if output should be captured."""
        return self.capture_output

    def is_text_mode(self) -> bool:
        """Check if text mode is enabled."""
        return self.text_mode

    def should_check_returncode(self) -> bool:
        """Check if return code should be checked (raise on non-zero)."""
        return self.check_returncode

    @classmethod
    def simple(cls, *command: str) -> ProcessCommand:
        """
        Create simple command with default settings.

        Args:
            *command: Command and arguments as separate strings

        Returns:
            ProcessCommand with default settings

        Examples:
            cmd = ProcessCommand.simple("ls", "-la")
            cmd = ProcessCommand.simple("docker", "ps", "-a")
        """
        return cls(command=list(command))

    @classmethod
    def for_runtime_check(cls, runtime: str) -> ProcessCommand:
        """
        Create command for runtime availability check.

        Args:
            runtime: Runtime name (docker, podman, etc.)

        Returns:
            ProcessCommand configured for version check
        """
        return cls(
            command=[runtime, "version"],
            timeout=5,
            capture_output=True,
            text_mode=True,
            check_returncode=True,
        )

    @classmethod
    def in_workspace(
        cls,
        command: list[str],
        workspace_path: str | Path,
        timeout: int = 30,
    ) -> ProcessCommand:
        """
        Create command to execute in workspace directory.

        Args:
            command: Command and arguments
            workspace_path: Working directory path
            timeout: Execution timeout in seconds

        Returns:
            ProcessCommand configured for workspace execution
        """
        return cls(
            command=command,
            working_directory=workspace_path,
            timeout=timeout,
            capture_output=True,
            text_mode=True,
            check_returncode=False,
        )

