"""Domain entity for step execution result."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # Avoid circular import
    pass


@dataclass(frozen=True)
class StepExecutionResult:
    """
    Result of executing a single step.

    This entity represents the outcome of executing a tool operation.
    It wraps the tool's domain entity result with execution metadata.
    """

    success: bool  # Whether the step succeeded
    result: Any  # The actual result from the tool (domain entity)
    error: str | None = None  # Error message if failed
    operation: str | None = None  # Operation name that was executed
    tool_name: str | None = None  # Tool name that was used

