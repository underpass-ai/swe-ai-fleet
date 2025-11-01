"""DTO for step execution result."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StepExecutionDTO:
    """
    DTO for step execution result returned by ExecuteTaskUseCase.

    This DTO represents the outcome of executing a single step.
    """

    success: bool
    result: Any | None
    error: str | None = None

    def __post_init__(self) -> None:
        """Validate DTO invariants."""
        if self.success is False and not self.error:
            # Allow success=False without error for cases where we just mark as failed
            # without a specific error message
            pass
