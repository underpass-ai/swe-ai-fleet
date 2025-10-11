# src/swe_ai_fleet/context/domain/plan_version.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from swe_ai_fleet.context.domain.graph_relationship import GraphRelationship


@dataclass(frozen=True)
class PlanVersion:
    """Domain model representing a PlanVersion entity in the context graph.

    A PlanVersion represents a specific version of a plan for completing a case.
    It serves as an intermediate entity connecting cases to their subtasks.
    """

    plan_id: str
    version: int
    case_id: str

    @staticmethod
    def from_payload(payload: dict[str, Any]) -> PlanVersion:
        """Create a PlanVersion from event payload data."""
        return PlanVersion(
            plan_id=payload["plan_id"], version=int(payload.get("version", 1)), case_id=payload["case_id"]
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert PlanVersion to dictionary representation."""
        return {
            "plan_id": self.plan_id,
            "version": self.version,
            "case_id": self.case_id,
        }

    def to_graph_properties(self) -> dict[str, Any]:
        """Convert PlanVersion to properties suitable for graph storage."""
        return {
            "plan_id": self.plan_id,  # Include ID for semantic queries
            "version": self.version,
            "case_id": self.case_id,  # Include for easier querying
        }

    def get_relationship_to_case(self) -> GraphRelationship:
        """Get the relationship details to connect this plan to its case."""
        return GraphRelationship(
            src_id=self.case_id,
            rel_type="HAS_PLAN",
            dst_id=self.plan_id,
            src_labels=["Case"],
            dst_labels=["PlanVersion"],
        )
