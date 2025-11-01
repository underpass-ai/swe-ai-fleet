"""Process execution result entity."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessResult:
    """
    Immutable entity representing the result of a process execution.

    Following DDD principles:
    - Immutable (frozen=True)
    - Fail-fast validation in __post_init__
    - Self-contained business logic
    """

    stdout: str
    stderr: str
    returncode: int
    command: list[str]

    def __post_init__(self) -> None:
        """
        Validate entity invariants (fail-fast).

        Raises:
            ValueError: If any invariant is violated
        """
        if self.stdout is None:
            raise ValueError("stdout is required (use empty string if no output) (fail-fast)")
        if self.stderr is None:
            raise ValueError("stderr is required (use empty string if no error) (fail-fast)")
        if not isinstance(self.returncode, int):
            raise ValueError("returncode must be an integer (fail-fast)")
        if not self.command:
            raise ValueError("command is required and cannot be empty (fail-fast)")
        if not isinstance(self.command, list):
            raise ValueError("command must be a list (fail-fast)")

    def is_success(self) -> bool:
        """
        Check if the process execution was successful (returncode == 0).

        Returns:
            True if process exited with code 0
        """
        return self.returncode == 0

    def has_output(self) -> bool:
        """
        Check if the process produced output in stdout.

        Returns:
            True if stdout is non-empty
        """
        return bool(self.stdout and self.stdout.strip())

    def has_errors(self) -> bool:
        """
        Check if the process produced errors in stderr.

        Returns:
            True if stderr is non-empty
        """
        return bool(self.stderr and self.stderr.strip())

    def get_combined_output(self) -> str:
        """
        Get combined output from stdout and stderr.

        Returns:
            Combined output with labeled sections
        """
        parts = []
        if self.stdout:
            parts.append(f"STDOUT:\n{self.stdout}")
        if self.stderr:
            parts.append(f"STDERR:\n{self.stderr}")
        return "\n\n".join(parts) if parts else "No output"

    def get_command_str(self) -> str:
        """
        Get command as shell-readable string.

        Returns:
            Command formatted as string
        """
        return " ".join(self.command)

    @classmethod
    def from_subprocess_result(cls, result: Any, command: list[str]) -> ProcessResult:
        """
        Create ProcessResult from subprocess.CompletedProcess.

        Args:
            result: subprocess.CompletedProcess instance
            command: Original command that was executed

        Returns:
            ProcessResult entity
        """
        return cls(
            stdout=result.stdout or "",
            stderr=result.stderr or "",
            returncode=result.returncode,
            command=command,
        )

