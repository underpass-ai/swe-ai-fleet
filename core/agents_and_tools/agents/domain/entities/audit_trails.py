"""Collection of audit trail entries."""

from dataclasses import dataclass, field

from core.agents_and_tools.agents.domain.entities.audit_trail import AuditTrailEntry


@dataclass
class AuditTrails:
    """Collection of audit trail entries with utility methods."""

    entries: list[AuditTrailEntry] = field(default_factory=list)  # List of AuditTrailEntry entities

    def add(self, entry: dict) -> None:
        """Add an audit trail entry."""
        from datetime import datetime

        # Convert dict to AuditTrailEntry entity
        audit_entry = AuditTrailEntry(
            timestamp=datetime.fromisoformat(entry["timestamp"]) if "timestamp" in entry else datetime.now(),
            event_type=entry.get("event_type", ""),
            details=entry.get("details", {}),
            success=entry.get("success", True),
            error=entry.get("error"),
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

    def to_dict(self) -> list[dict]:
        """Convert to list of dicts for serialization."""
        return [
            {
                "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
                "event_type": entry.event_type,
                "details": entry.details,
                "success": entry.success,
                "error": entry.error,
            }
            for entry in self.entries
        ]

