"""StepResult: Value object representing the result of step execution."""

from dataclasses import dataclass
from typing import Any

from core.ceremony_engine.domain.value_objects.step_status import StepStatus


@dataclass(frozen=True)
class StepResult:
    """
    Value Object: Result of step execution.

    Domain Invariants:
    - status must be a valid StepStatus
    - output must be a dict (can be empty for failures)
    - error_message is optional (required if status is FAILED)
    - Immutable (frozen=True)

    Business Rules:
    - COMPLETED steps must have output (can be empty dict)
    - FAILED steps should have error_message
    - PENDING/IN_PROGRESS should not be used in StepResult (only terminal statuses)
    """

    status: StepStatus
    output: dict[str, Any]
    error_message: str | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Validate business invariants (fail-fast).

        Raises:
            ValueError: If result is invalid
        """
        if not isinstance(self.status, StepStatus):
            raise ValueError(f"status must be a StepStatus, got {type(self.status)}")

        if not isinstance(self.output, dict):
            raise ValueError(f"output must be a dict, got {type(self.output)}")

        # Terminal statuses only (PENDING/IN_PROGRESS are runtime states, not results)
        if self.status in {StepStatus.PENDING, StepStatus.IN_PROGRESS}:
            raise ValueError(
                f"StepResult cannot have status {self.status} (use terminal statuses only)"
            )

        # FAILED status should have error_message
        if self.status == StepStatus.FAILED and not self.error_message:
            raise ValueError("FAILED StepResult must have error_message")

        # COMPLETED status should not have error_message
        if self.status == StepStatus.COMPLETED and self.error_message:
            raise ValueError("COMPLETED StepResult should not have error_message")

    def is_success(self) -> bool:
        """Check if result represents successful completion.

        Returns:
            True if status is COMPLETED
        """
        return self.status == StepStatus.COMPLETED

    def is_failure(self) -> bool:
        """Check if result represents a failure.

        Returns:
            True if status is FAILED or CANCELLED
        """
        return self.status in {StepStatus.FAILED, StepStatus.CANCELLED}
