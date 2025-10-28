"""Domain entity for tool operation."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Operation:
    """Single tool operation executed by agent."""

    tool_name: str  # Name of the tool (e.g., "FileTool")
    operation: str  # Name of the operation (e.g., "write_file")
    params: dict[str, Any]  # Parameters passed to the operation
    result: dict[str, Any]  # Result from the operation
    timestamp: datetime  # When the operation was executed
    success: bool  # Whether the operation succeeded
    error: str | None = None  # Error message if failed
    duration_ms: int | None = None  # Execution duration in milliseconds

