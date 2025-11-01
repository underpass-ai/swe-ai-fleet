"""Domain entity for observation history entry."""

from dataclasses import dataclass
from typing import Any

from core.agents_and_tools.agents.domain.entities.core.execution_step import ExecutionStep


@dataclass(frozen=True)
class Observation:
    """Single observation from agent execution."""

    iteration: int  # Iteration number
    action: ExecutionStep  # The action that was executed (ExecutionStep entity)
    result: Any  # Result from the operation
    success: bool  # Whether the operation succeeded
    error: str | None = None  # Error message if failed

