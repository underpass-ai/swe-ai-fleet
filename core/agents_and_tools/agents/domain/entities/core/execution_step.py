"""Domain entity for execution step."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ExecutionStep:
    """
    Represents a single step in an execution plan.
    
    This entity encapsulates what operation to execute on which tool,
    with optional parameters.
    """
    
    tool: str
    operation: str
    params: dict[str, Any] | None = None
    
    def __post_init__(self) -> None:
        """Validate step invariants."""
        if not self.tool:
            raise ValueError("tool cannot be empty")
        if not self.operation:
            raise ValueError("operation cannot be empty")

