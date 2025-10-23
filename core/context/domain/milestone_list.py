from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from .milestone import Milestone


@dataclass(frozen=True)
class MilestoneList:
    milestones: list[Milestone] = field(default_factory=list)

    def to_sorted_dicts(self) -> list[dict[str, Any]]:
        sorted_milestones = sorted(self.milestones, key=lambda milestone: milestone.ts_ms)
        return [m.to_dict() for m in sorted_milestones]

    @staticmethod
    def build_from_events(events: Iterable[Any], allowed_events: set[str]) -> MilestoneList:
        built: list[Milestone] = []
        for ev in events:
            if ev.event in allowed_events:
                built.append(Milestone(ts_ms=ev.ts_ms, event=ev.event, actor=ev.actor))
        return MilestoneList(milestones=built)
