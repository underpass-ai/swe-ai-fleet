from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..utils import AttrUtils


@dataclass(frozen=True)
class PlanHeader:
    plan_id: str
    status: str
    version: int
    rationale: str

    @staticmethod
    def from_sources(graph_plan: Any | None, redis_plan: Any | None) -> PlanHeader:
        return PlanHeader(
            plan_id=AttrUtils.pick_attr(graph_plan, redis_plan, "plan_id", default=""),
            status=AttrUtils.pick_attr(graph_plan, redis_plan, "status", default="UNKNOWN"),
            version=AttrUtils.pick_attr(graph_plan, redis_plan, "version", default=0),
            rationale=AttrUtils.pick_attr(graph_plan, redis_plan, "rationale", default=""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "status": self.status,
            "version": self.version,
            "rationale": self.rationale,
        }
