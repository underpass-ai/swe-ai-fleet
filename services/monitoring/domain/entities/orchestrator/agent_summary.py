"""Agent summary value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING


@dataclass(frozen=True)
class AgentSummary:
    """Value object representing a summary of agent statuses.

    This immutable value object encapsulates the count of agents
    by their status, providing domain-specific operations for
    analyzing agent distribution.
    """

    ready_count: int
    idle_count: int
    busy_count: int
    error_count: int
    offline_count: int

    @classmethod
    def create(cls, ready_count: int = 0, idle_count: int = 0, busy_count: int = 0,
               error_count: int = 0, offline_count: int = 0) -> AgentSummary:
        """Create AgentSummary with validation.

        Args:
            ready_count: Number of ready agents
            idle_count: Number of idle agents
            busy_count: Number of busy agents
            error_count: Number of agents with errors
            offline_count: Number of offline agents

        Returns:
            AgentSummary instance

        Raises:
            ValueError: If any count is negative
        """
        if ready_count < 0:
            raise ValueError("Ready count cannot be negative")
        if idle_count < 0:
            raise ValueError("Idle count cannot be negative")
        if busy_count < 0:
            raise ValueError("Busy count cannot be negative")
        if error_count < 0:
            raise ValueError("Error count cannot be negative")
        if offline_count < 0:
            raise ValueError("Offline count cannot be negative")

        return cls(
            ready_count=ready_count,
            idle_count=idle_count,
            busy_count=busy_count,
            error_count=error_count,
            offline_count=offline_count
        )

    @classmethod
    def from_status_dict(cls, status_dict: dict[str, int]) -> AgentSummary:
        """Create AgentSummary from status dictionary.

        Args:
            status_dict: Dictionary with status as key and count as value

        Returns:
            AgentSummary instance
        """
        return cls.create(
            ready_count=status_dict.get("ready", 0),
            idle_count=status_dict.get("idle", 0),
            busy_count=status_dict.get("busy", 0),
            error_count=status_dict.get("error", 0),
            offline_count=status_dict.get("offline", 0)
        )

    def total_agents(self) -> int:
        """Get total number of agents.

        Tell, Don't Ask: Tell summary to provide total count.

        Returns:
            Total number of agents
        """
        return self.ready_count + self.idle_count + self.busy_count + self.error_count + self.offline_count

    def has_ready_agents(self) -> bool:
        """Check if there are any ready agents.

        Tell, Don't Ask: Tell summary to check if it has ready agents.

        Returns:
            True if there are ready agents, False otherwise
        """
        return self.ready_count > 0

    def has_busy_agents(self) -> bool:
        """Check if there are any busy agents.

        Tell, Don't Ask: Tell summary to check if it has busy agents.

        Returns:
            True if there are busy agents, False otherwise
        """
        return self.busy_count > 0

    def has_offline_agents(self) -> bool:
        """Check if there are any offline agents.

        Tell, Don't Ask: Tell summary to check if it has offline agents.

        Returns:
            True if there are offline agents, False otherwise
        """
        return self.offline_count > 0

    def has_error_agents(self) -> bool:
        """Check if there are any agents with errors.

        Tell, Don't Ask: Tell summary to check if it has error agents.

        Returns:
            True if there are error agents, False otherwise
        """
        return self.error_count > 0

    def is_all_ready(self) -> bool:
        """Check if all agents are ready.

        Tell, Don't Ask: Tell summary to check if all agents are ready.

        Returns:
            True if all agents are ready, False otherwise
        """
        return self.total_agents() > 0 and self.ready_count == self.total_agents()

    def is_all_offline(self) -> bool:
        """Check if all agents are offline.

        Tell, Don't Ask: Tell summary to check if all agents are offline.

        Returns:
            True if all agents are offline, False otherwise
        """
        return self.total_agents() > 0 and self.offline_count == self.total_agents()

    def get_availability_percentage(self) -> float:
        """Get percentage of available agents (ready + idle).

        Tell, Don't Ask: Tell summary to provide availability percentage.

        Returns:
            Percentage of available agents (0.0 to 100.0)
        """
        total = self.total_agents()
        if total == 0:
            return 0.0

        available = self.ready_count + self.idle_count
        return (available / total) * 100.0

    def to_dict(self) -> dict[str, int]:
        """Convert summary to dictionary representation.

        Used for serialization and API responses.

        Returns:
            Dictionary with status counts
        """
        return {
            "ready": self.ready_count,
            "idle": self.idle_count,
            "busy": self.busy_count,
            "error": self.error_count,
            "offline": self.offline_count,
            "total": self.total_agents()
        }
