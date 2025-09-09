# src/swe_ai_fleet/context/domain/graph_relationship.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GraphRelationship:
    """Domain model representing a relationship between entities in the context graph.

    This model encapsulates the structure and properties of relationships
    between different entities in the graph database.
    """

    src_id: str
    rel_type: str
    dst_id: str
    src_labels: list[str] | None = None
    dst_labels: list[str] | None = None
    properties: dict[str, Any] | None = None

    @staticmethod
    def affects_relationship(decision_id: str, subtask_id: str) -> GraphRelationship:
        """Create an AFFECTS relationship between a decision and subtask."""
        return GraphRelationship(
            src_id=decision_id,
            rel_type="AFFECTS",
            dst_id=subtask_id,
            src_labels=["Decision"],
            dst_labels=["Subtask"],
        )

    @staticmethod
    def has_plan_relationship(case_id: str, plan_id: str) -> GraphRelationship:
        """Create a HAS_PLAN relationship between a case and plan."""
        return GraphRelationship(
            src_id=case_id,
            rel_type="HAS_PLAN",
            dst_id=plan_id,
            src_labels=["Case"],
            dst_labels=["PlanVersion"],
        )

    @staticmethod
    def has_subtask_relationship(plan_id: str, subtask_id: str) -> GraphRelationship:
        """Create a HAS_SUBTASK relationship between a plan and subtask."""
        return GraphRelationship(
            src_id=plan_id,
            rel_type="HAS_SUBTASK",
            dst_id=subtask_id,
            src_labels=["PlanVersion"],
            dst_labels=["Subtask"],
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert GraphRelationship to dictionary representation."""
        return {
            "src_id": self.src_id,
            "rel_type": self.rel_type,
            "dst_id": self.dst_id,
            "src_labels": self.src_labels,
            "dst_labels": self.dst_labels,
            "properties": self.properties,
        }

    def get_cypher_pattern(self) -> str:
        """Generate the Cypher pattern for this relationship."""
        src_label_expr = ":" + ":".join(sorted(set(self.src_labels))) if self.src_labels else ""
        dst_label_expr = ":" + ":".join(sorted(set(self.dst_labels))) if self.dst_labels else ""

        return (
            f"MATCH (a{src_label_expr} {{id:$src}}), (b{dst_label_expr} {{id:$dst}}) "
            f"MERGE (a)-[r:{self.rel_type}]->(b) SET r += $props"
        )
