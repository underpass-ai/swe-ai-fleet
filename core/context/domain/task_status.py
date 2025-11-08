"""TaskStatus enum - Status states for tasks."""

from enum import Enum


class TaskStatus(str, Enum):
    """Status states for tasks in the system.

    These states track task progression through the workflow.
    """

    # Initial state
    TODO = "todo"
    PENDING = "pending"

    # Active states
    IN_PROGRESS = "in_progress"
    IMPLEMENTING = "implementing"
    TESTING = "testing"

    # Review states
    PENDING_REVIEW = "pending_review"
    IN_REVIEW = "in_review"
    CHANGES_REQUESTED = "changes_requested"

    # Terminal states
    DONE = "done"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"

    # Error states
    FAILED = "failed"
    ERROR = "error"

    def __str__(self) -> str:
        """Return the string value."""
        return self.value

    def is_terminal(self) -> bool:
        """Check if this is a terminal state (no further transitions).

        Returns:
            True if terminal state
        """
        return self in {
            TaskStatus.DONE,
            TaskStatus.COMPLETED,
            TaskStatus.CANCELLED,
            TaskStatus.FAILED,
        }

    def is_active(self) -> bool:
        """Check if task is actively being worked on.

        Returns:
            True if in active state
        """
        return self in {
            TaskStatus.IN_PROGRESS,
            TaskStatus.IMPLEMENTING,
            TaskStatus.TESTING,
        }






