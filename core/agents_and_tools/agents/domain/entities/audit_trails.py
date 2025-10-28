"""Collection of audit trail entries."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.agents_and_tools.agents.domain.entities.audit_trail import AuditTrailEntry


@dataclass
class AuditTrails:
    """Collection of audit trail entries with utility methods."""

    entries: list[dict] = field(default_factory=list)  # List of audit entries

    def add(self, entry: dict) -> None:
        """Add an audit trail entry."""
        self.entries.append(entry)

    def get_all(self) -> list[dict]:
        """Get all audit trail entries."""
        return self.entries

    def get_by_event_type(self, event_type: str) -> list[dict]:
        """Get all entries with a specific event type."""
        return [entry for entry in self.entries if entry.get("event_type") == event_type]

    def get_errors(self) -> list[dict]:
        """Get all error entries."""
        return [entry for entry in self.entries if not entry.get("success", True)]

    def count(self) -> int:
        """Get the number of audit entries."""
        return len(self.entries)

    def to_dict(self) -> list[dict]:
        """Convert to list of dicts for serialization."""
        return self.entries

