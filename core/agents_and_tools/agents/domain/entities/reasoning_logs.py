"""Collection of reasoning log entries."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.agents_and_tools.agents.domain.entities.reasoning_log import ReasoningLogEntry


@dataclass
class ReasoningLogs:
    """Collection of reasoning log entries with utility methods."""

    entries: list[dict] = field(default_factory=list)  # List of reasoning entries

    def add(self, entry: dict) -> None:
        """Add a reasoning log entry."""
        self.entries.append(entry)

    def get_all(self) -> list[dict]:
        """Get all reasoning entries."""
        return self.entries

    def get_by_thought_type(self, thought_type: str) -> list[dict]:
        """Get all entries with a specific thought type."""
        return [entry for entry in self.entries if entry.get("type") == thought_type]

    def get_by_iteration(self, iteration: int) -> list[dict]:
        """Get all entries for a specific iteration."""
        return [entry for entry in self.entries if entry.get("iteration") == iteration]

    def get_last_n(self, n: int) -> list[dict]:
        """Get the last n entries."""
        return self.entries[-n:] if len(self.entries) >= n else self.entries

    def count(self) -> int:
        """Get the number of reasoning entries."""
        return len(self.entries)

    def to_dict(self) -> list[dict]:
        """Convert to list of dicts for serialization."""
        return self.entries

