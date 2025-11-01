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


