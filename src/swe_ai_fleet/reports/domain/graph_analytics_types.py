

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CriticalNode:
    id: str
    label: str  # e.g. "Decision"
    score: float  # centrality/indegree fallback




@dataclass(frozen=True)
class PathCycle:
    nodes: list[str]
    rels: list[str]




@dataclass(frozen=True)
class LayeredTopology:
    layers: list[list[str]]  # layer 0 -> ... -> N




@dataclass(frozen=True)
class AgentMetrics:
    agent_id: str
    total_runs: int
    success_rate: float
    p50_duration_ms: float
    p95_duration_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "total_runs": self.total_runs,
            "success_rate": self.success_rate,
            "p50_duration_ms": self.p50_duration_ms,
            "p95_duration_ms": self.p95_duration_ms,
        }