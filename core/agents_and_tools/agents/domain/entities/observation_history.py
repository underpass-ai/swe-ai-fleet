"""Domain entity for observation history entry."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Observation:
    """Single observation from agent execution."""

    tool: str  # Name of the tool
    operation: str  # Name of the operation
    success: bool  # Whether the operation succeeded
    result: dict[str, Any]  # Result from the operation
    error: str | None = None  # Error message if failed

