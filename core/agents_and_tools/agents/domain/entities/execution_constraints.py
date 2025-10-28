"""Execution constraints for agent tasks."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionConstraints:
    """
    Execution constraints for agent task execution.
    
    This entity represents the configuration and limits for executing a task,
    including planning mode, limits on operations, and error handling behavior.
    
    Attributes:
        max_operations: Maximum number of tool operations allowed (default: 100)
        abort_on_error: Stop execution on first error (default: True)
        iterative: Use iterative planning instead of static (default: False)
        max_iterations: Maximum iterations if iterative mode (default: 10)
    """

    max_operations: int = 100
    abort_on_error: bool = True
    iterative: bool = False
    max_iterations: int = 10

    @classmethod
    def from_dict(cls, data: dict | None) -> ExecutionConstraints:
        """
        Create ExecutionConstraints from dictionary.
        
        Args:
            data: Dictionary with constraint values (can be None)
            
        Returns:
            ExecutionConstraints instance with default values if data is None
        """
        if data is None:
            return ExecutionConstraints()
        
        return ExecutionConstraints(
            max_operations=data.get("max_operations", 100),
            abort_on_error=data.get("abort_on_error", True),
            iterative=data.get("iterative", False),
            max_iterations=data.get("max_iterations", 10),
        )

    def to_dict(self) -> dict:
        """
        Convert ExecutionConstraints to dictionary.
        
        Returns:
            Dictionary representation of constraints
        """
        return {
            "max_operations": self.max_operations,
            "abort_on_error": self.abort_on_error,
            "iterative": self.iterative,
            "max_iterations": self.max_iterations,
        }

