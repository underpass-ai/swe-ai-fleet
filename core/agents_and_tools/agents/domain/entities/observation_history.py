"""Domain entity for observation history entry."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Observation:
    """Single observation from agent execution."""

    iteration: int  # Iteration number
    action: dict[str, Any]  # The action that was executed (step_info)
    result: Any  # Result from the operation
    success: bool  # Whether the operation succeeded
    error: str | None = None  # Error message if failed

