"""Docker operations registry entity."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class DockerOperations:
    """
    Immutable entity representing available Docker operations.
    
    Following DDD principles:
    - Immutable (frozen=True)
    - Fail-fast validation in __post_init__
    - Maps operation names to their implementations
    """

    build: Callable
    run: Callable
    exec: Callable
    ps: Callable
    logs: Callable
    stop: Callable
    rm: Callable

    def __post_init__(self) -> None:
        """
        Validate entity invariants (fail-fast).
        
        Raises:
            ValueError: If any operation is not callable
        """
        operations = {
            "build": self.build,
            "run": self.run,
            "exec": self.exec,
            "ps": self.ps,
            "logs": self.logs,
            "stop": self.stop,
            "rm": self.rm,
        }
        
        for op_name, op_func in operations.items():
            if not callable(op_func):
                raise ValueError(f"{op_name} must be callable (fail-fast)")

    def to_dict(self) -> dict[str, Callable]:
        """
        Convert operations to dictionary mapping.
        
        Note: This method is allowed because it provides the MCP interface
        that external systems expect.
        
        Returns:
            Dictionary mapping operation names to their implementations
        """
        return {
            "build": self.build,
            "run": self.run,
            "exec": self.exec,
            "ps": self.ps,
            "logs": self.logs,
            "stop": self.stop,
            "rm": self.rm,
        }

    def get_operation(self, name: str) -> Callable | None:
        """
        Get operation by name.
        
        Args:
            name: Operation name (build, run, exec, ps, logs, stop, rm)
            
        Returns:
            Callable for the operation, or None if not found
        """
        operations = self.to_dict()
        return operations.get(name)

    def has_operation(self, name: str) -> bool:
        """
        Check if operation exists.
        
        Args:
            name: Operation name
            
        Returns:
            True if operation exists, False otherwise
        """
        return name in self.to_dict()

    def list_operations(self) -> list[str]:
        """
        Get list of all available operation names.
        
        Returns:
            List of operation names
        """
        return list(self.to_dict().keys())

    def count_operations(self) -> int:
        """
        Get count of available operations.
        
        Returns:
            Number of operations
        """
        return len(self.to_dict())

