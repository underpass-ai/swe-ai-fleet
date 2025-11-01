"""Container exec configuration value object."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContainerExecConfig:
    """
    Immutable value object representing container exec configuration.
    
    Following DDD principles:
    - Immutable (frozen=True)
    - Fail-fast validation in __post_init__
    - Self-contained business logic
    """

    container: str
    command: list[str]
    timeout: int = 60

    def __post_init__(self) -> None:
        """
        Validate value object invariants (fail-fast).
        
        Raises:
            ValueError: If any invariant is violated
        """
        if not self.container or not self.container.strip():
            raise ValueError("container is required and cannot be empty (fail-fast)")
        
        if not self.command or not isinstance(self.command, list):
            raise ValueError("command is required and must be a non-empty list (fail-fast)")
        
        if len(self.command) == 0:
            raise ValueError("command cannot be empty (fail-fast)")
        
        if not isinstance(self.timeout, int):
            raise ValueError("timeout must be an integer (fail-fast)")
        
        if self.timeout <= 0:
            raise ValueError("timeout must be positive (fail-fast)")

    def get_command_string(self) -> str:
        """
        Get command as a single string for logging.
        
        Returns:
            Space-separated command string
        """
        return " ".join(self.command)

    def has_shell_command(self) -> bool:
        """
        Check if command is a shell command.
        
        Returns:
            True if command starts with 'sh' or 'bash'
        """
        if not self.command:
            return False
        return self.command[0] in ("sh", "bash", "/bin/sh", "/bin/bash")

    @classmethod
    def simple(cls, container: str, command: list[str]) -> ContainerExecConfig:
        """
        Create simple exec config with default timeout.
        
        Args:
            container: Container name or ID
            command: Command to execute
            
        Returns:
            ContainerExecConfig with default timeout (60s)
        """
        return cls(container=container, command=command)

    @classmethod
    def with_timeout(cls, container: str, command: list[str], timeout: int) -> ContainerExecConfig:
        """
        Create exec config with custom timeout.
        
        Args:
            container: Container name or ID
            command: Command to execute
            timeout: Timeout in seconds
            
        Returns:
            ContainerExecConfig with custom timeout
        """
        return cls(container=container, command=command, timeout=timeout)

