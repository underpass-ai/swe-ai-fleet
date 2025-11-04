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
        """Validate step invariants (fail-fast)."""
        if not self.tool or not self.tool.strip():
            raise ValueError("tool cannot be empty or whitespace")
        if not self.operation or not self.operation.strip():
            raise ValueError("operation cannot be empty or whitespace")

