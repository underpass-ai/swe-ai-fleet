"""Collection of audit trail entries."""

from dataclasses import dataclass, field
from typing import Any

from core.agents_and_tools.agents.domain.entities.collections.audit_trail import AuditTrailEntry


@dataclass
class AuditTrails:
    """Collection of audit trail entries with utility methods."""

    entries: list[AuditTrailEntry] = field(default_factory=list)  # List of AuditTrailEntry entities

    def add(
        self,
        event_type: str,
        details: dict[str, Any],
        success: bool = True,
        error: str | None = None,
    ) -> None:
        """Add an audit trail entry."""
        from datetime import datetime

        audit_entry = AuditTrailEntry(
            timestamp=datetime.now(),
            event_type=event_type,
            details=details,
            success=success,
            error=error,
        )
        self.entries.append(audit_entry)

    def get_all(self) -> list[AuditTrailEntry]:
        """Get all audit trail entries."""
        return self.entries

    def get_by_event_type(self, event_type: str) -> list[AuditTrailEntry]:
        """Get all entries with a specific event type."""
        return [entry for entry in self.entries if entry.event_type == event_type]

    def get_errors(self) -> list[AuditTrailEntry]:
        """Get all error entries."""
        return [entry for entry in self.entries if not entry.success]

    def count(self) -> int:
        """Get the number of audit entries."""
        return len(self.entries)

