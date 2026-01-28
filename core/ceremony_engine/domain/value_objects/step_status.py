"""StepStatus: Enumeration of step execution status."""

from enum import Enum


class StepStatus(str, Enum):
    """
    Enumeration of step execution status.

    Status transitions:
    - PENDING → IN_PROGRESS (when step execution starts)
    - IN_PROGRESS → COMPLETED (when step succeeds)
    - IN_PROGRESS → FAILED (when step fails)
    - IN_PROGRESS → WAITING_FOR_HUMAN (for human_gate_step)
    - WAITING_FOR_HUMAN → COMPLETED (when human approves)
    - WAITING_FOR_HUMAN → FAILED (when human rejects)
    - Any → CANCELLED (when ceremony is cancelled)

    Business Rules:
    - PENDING: Step is ready to execute but hasn't started
    - IN_PROGRESS: Step is currently executing
    - COMPLETED: Step finished successfully
    - FAILED: Step execution failed (may be retried)
    - WAITING_FOR_HUMAN: Step requires human approval (human_gate_step)
    - CANCELLED: Step was cancelled (ceremony terminated)
    """

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    WAITING_FOR_HUMAN = "WAITING_FOR_HUMAN"
    CANCELLED = "CANCELLED"

    def is_terminal(self) -> bool:
        """Check if this is a terminal status (no further execution).

        Returns:
            True if COMPLETED, FAILED, or CANCELLED
        """
        return self in {
            StepStatus.COMPLETED,
            StepStatus.FAILED,
            StepStatus.CANCELLED,
        }

    def is_executable(self) -> bool:
        """Check if step can be executed from this status.

        Returns:
            True if PENDING, FAILED (retry), or WAITING_FOR_HUMAN
            (re-execution with human approval context).
        """
        return self in {
            StepStatus.PENDING,
            StepStatus.FAILED,
            StepStatus.WAITING_FOR_HUMAN,
        }

    def is_success(self) -> bool:
        """Check if this status represents successful completion.

        Returns:
            True if COMPLETED
        """
        return self == StepStatus.COMPLETED

    def is_failure(self) -> bool:
        """Check if this status represents a failure.

        Returns:
            True if FAILED or CANCELLED
        """
        return self in {StepStatus.FAILED, StepStatus.CANCELLED}
