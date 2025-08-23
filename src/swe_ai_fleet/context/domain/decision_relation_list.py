from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from swe_ai_fleet.reports.domain.decision_edges import DecisionEdges
from swe_ai_fleet.reports.domain.decision_node import DecisionNode

from .decision_relation import DecisionRelation


@dataclass(frozen=True)
class DecisionRelationList:
    relations: list[DecisionRelation] = field(default_factory=list)

    def to_dicts(self) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self.relations]

    @staticmethod
    def build(
        relevant_decisions: list[DecisionNode],
        dependencies_by_source: dict[str, list[DecisionEdges]],
    ) -> DecisionRelationList:
        built: list[DecisionRelation] = []
        for decision in relevant_decisions:
            for edge in dependencies_by_source.get(decision.id, []):
                built.append(DecisionRelation(edge.src_id, edge.rel_type, edge.dst_id))
        return DecisionRelationList(relations=built)
