"""EpicStatus enum - Status states for epics."""

from enum import Enum


class EpicStatus(str, Enum):
    """Status states for Epics in the system.

    Epics have a simpler lifecycle than Stories (no FSM needed).
    They serve as containers for grouping related stories.
    """

    # Active states
    ACTIVE = "active"  # Epic is currently being worked on
    PLANNING = "planning"  # Epic is being planned, stories being defined
    IN_PROGRESS = "in_progress"  # Some stories are in progress

    # Terminal states
    COMPLETED = "completed"  # All stories completed
    ARCHIVED = "archived"  # Epic archived for historical reference
    CANCELLED = "cancelled"  # Epic cancelled, no longer relevant

    def __str__(self) -> str:
        """Return the string value."""
        return self.value

    def is_terminal(self) -> bool:
        """Check if this is a terminal state (no further work).

        Returns:
            True if terminal state
        """
        return self in {
            EpicStatus.COMPLETED,
            EpicStatus.ARCHIVED,
            EpicStatus.CANCELLED,
        }

    def is_active_work(self) -> bool:
        """Check if epic has active work ongoing.

        Returns:
            True if epic is actively being worked on
        """
        return self in {
            EpicStatus.ACTIVE,
            EpicStatus.PLANNING,
            EpicStatus.IN_PROGRESS,
        }

