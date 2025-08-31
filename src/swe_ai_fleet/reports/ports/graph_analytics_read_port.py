from __future__ import annotations

from typing import Protocol

from swe_ai_fleet.reports.domain.graph_analytics_types import (
    AgentMetrics,
    CriticalNode,
    LayeredTopology,
    PathCycle,
)


class GraphAnalyticsReadPort(Protocol):
    """Read-only analytics queries over the decision graph.

    All methods are **scoped to the latest PlanVersion** of the provided case.
    Implementations should prefer parameterized Cypher and avoid dynamic string concatenation.
    """

    def get_critical_decisions(self, case_id: str, limit: int = 10) -> list[CriticalNode]: ...

    def find_cycles(self, case_id: str, max_depth: int = 6) -> list[PathCycle]: ...

    def topo_layers(self, case_id: str) -> LayeredTopology: ...

    # Optional: not implemented in the adapter yet (kept for future Mx)
    def agent_metrics(self, agent_id: str, since_iso: str) -> AgentMetrics: ...