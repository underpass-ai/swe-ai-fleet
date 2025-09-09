# src/swe_ai_fleet/context/domain/case.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Case:
    """Domain model representing a Case entity in the context graph.

    A Case represents a software engineering task or project that needs to be completed.
    It serves as the root entity in the context graph, connecting to plans, subtasks, and decisions.
    """

    case_id: str
    name: str

    @staticmethod
    def from_payload(payload: dict[str, Any]) -> Case:
        """Create a Case from event payload data."""
        return Case(case_id=payload["case_id"], name=payload.get("name", ""))

    def to_dict(self) -> dict[str, Any]:
        """Convert Case to dictionary representation."""
        return {
            "case_id": self.case_id,
            "name": self.name,
        }

    def to_graph_properties(self) -> dict[str, Any]:
        """Convert Case to properties suitable for graph storage."""
        return {
            "name": self.name,
        }
