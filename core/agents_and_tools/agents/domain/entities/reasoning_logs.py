"""Collection of reasoning log entries."""

from dataclasses import dataclass, field

from core.agents_and_tools.agents.domain.entities.reasoning_log import ReasoningLogEntry


@dataclass
class ReasoningLogs:
    """Collection of reasoning log entries with utility methods."""

    entries: list[ReasoningLogEntry] = field(default_factory=list)  # List of ReasoningLogEntry entities

    def add(self, entry: dict) -> None:
        """Add a reasoning log entry."""
        from datetime import datetime
        
        # Convert dict to ReasoningLogEntry entity
        log_entry = ReasoningLogEntry(
            agent_id=entry.get("agent_id", ""),
            role=entry.get("role", ""),
            iteration=entry.get("iteration", 0),
            thought_type=entry.get("type", ""),
            content=entry.get("content", ""),
            related_operations=entry.get("related_operations", []),
            confidence=entry.get("confidence"),
            timestamp=datetime.fromisoformat(entry["timestamp"]) if "timestamp" in entry else datetime.now(),
        )
        self.entries.append(log_entry)

    def get_all(self) -> list[ReasoningLogEntry]:
        """Get all reasoning entries."""
        return self.entries

    def get_by_thought_type(self, thought_type: str) -> list[ReasoningLogEntry]:
        """Get all entries with a specific thought type."""
        return [entry for entry in self.entries if entry.thought_type == thought_type]

    def get_by_iteration(self, iteration: int) -> list[ReasoningLogEntry]:
        """Get all entries for a specific iteration."""
        return [entry for entry in self.entries if entry.iteration == iteration]

    def get_last_n(self, n: int) -> list[ReasoningLogEntry]:
        """Get the last n entries."""
        return self.entries[-n:] if len(self.entries) >= n else self.entries

    def count(self) -> int:
        """Get the number of reasoning entries."""
        return len(self.entries)

    def to_dict(self) -> list[dict]:
        """Convert to list of dicts for serialization."""
        return [
            {
                "agent_id": entry.agent_id,
                "role": entry.role,
                "iteration": entry.iteration,
                "type": entry.thought_type,
                "content": entry.content,
                "related_operations": entry.related_operations,
                "confidence": entry.confidence,
                "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
            }
            for entry in self.entries
        ]

