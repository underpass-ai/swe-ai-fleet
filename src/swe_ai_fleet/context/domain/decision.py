# src/swe_ai_fleet/context/domain/decision.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Decision:
    """Domain model representing a Decision entity in the context graph.

    A Decision represents an architectural or design choice made during the development process.
    Decisions can affect subtasks and influence the overall project direction.
    """

    node_id: str
    kind: str
    summary: str
    sub_id: str | None = None

    @staticmethod
    def from_payload(payload: dict[str, Any]) -> Decision:
        """Create a Decision from event payload data."""
        return Decision(
            node_id=payload["node_id"],
            kind=payload.get("kind", ""),
            summary=payload.get("summary", ""),
            sub_id=payload.get("sub_id"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert Decision to dictionary representation."""
        return {
            "node_id": self.node_id,
            "kind": self.kind,
            "summary": self.summary,
            "sub_id": self.sub_id,
        }

    def to_graph_properties(self) -> dict[str, Any]:
        """Convert Decision to properties suitable for graph storage."""
        return {
            "kind": self.kind,
            "summary": self.summary,
        }

    def affects_subtask(self) -> bool:
        """Check if this decision affects a specific subtask."""
        return self.sub_id is not None
