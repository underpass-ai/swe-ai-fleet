"""TaskStatus enum for Planning Service."""

from enum import Enum


class TaskStatus(str, Enum):
    """Status states for Tasks.

    Tasks follow a simple workflow from creation to completion.
    """

    # Active states
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    BLOCKED = "blocked"

    # Terminal states
    COMPLETED = "completed"
    CANCELLED = "cancelled"

    def __str__(self) -> str:
        """Return string value.

        Returns:
            String representation
        """
        return self.value

    def is_terminal(self) -> bool:
        """Check if this is a terminal state.

        Returns:
            True if terminal
        """
        return self in {
            TaskStatus.COMPLETED,
            TaskStatus.CANCELLED,
        }

    def is_active_work(self) -> bool:
        """Check if task has active work.

        Returns:
            True if active work ongoing
        """
        return self in {
            TaskStatus.TODO,
            TaskStatus.IN_PROGRESS,
            TaskStatus.IN_REVIEW,
            TaskStatus.BLOCKED,
        }

