"""EpicStatus enum for Planning Service."""

from enum import Enum


class EpicStatus(str, Enum):
    """Status states for Epics.

    Epics have a simpler lifecycle than Stories (no FSM).
    They serve as containers for grouping related stories.
    """

    # Active states
    ACTIVE = "active"
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"

    # Terminal states
    COMPLETED = "completed"
    ARCHIVED = "archived"
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
            EpicStatus.COMPLETED,
            EpicStatus.ARCHIVED,
            EpicStatus.CANCELLED,
        }

    def is_active_work(self) -> bool:
        """Check if epic has active work.

        Returns:
            True if active work ongoing
        """
        return self in {
            EpicStatus.ACTIVE,
            EpicStatus.PLANNING,
            EpicStatus.IN_PROGRESS,
        }

