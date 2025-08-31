from __future__ import annotations

from collections import defaultdict
from typing import Any

from swe_ai_fleet.memory.neo4j_store import Neo4jStore
from swe_ai_fleet.reports.domain.graph_analytics_types import (
    AgentMetrics,
    CriticalNode,
    LayeredTopology,
    PathCycle,
)
from swe_ai_fleet.reports.ports.graph_analytics_read_port import GraphAnalyticsReadPort


class Neo4jGraphAnalyticsReadAdapter(GraphAnalyticsReadPort):
    """Analytics adapter using a thin `Neo4jStore` wrapper.

    It assumes the decision graph is projected as in the decision read adapter:
    (:Case {id})-[:HAS_PLAN]->(:PlanVersion)
    (:PlanVersion)-[:CONTAINS_DECISION]->(:Decision)
    (Decision)-[REL]->(Decision) with domain relations (e.g. DEPENDS_ON, GOVERNS, BLOCKS, ...)

    Notes:
    * All queries are **scoped to the latest PlanVersion** of the case.
    * We avoid relying on GDS; we provide indegree-based fallback and in-Python layering.
    """

    def __init__(self, store: Neo4jStore) -> None:
        self._store = store

    # ---------- Critical decisions (indegree fallback) ----------
    def get_critical_decisions(self, case_id: str, limit: int = 10) -> list[CriticalNode]:
        # Use a subgraph of Decision nodes under the latest PlanVersion for this case.
        q = (
            "MATCH (c:Case {id:$cid})-[:HAS_PLAN]->(p:PlanVersion)\n"
            "WITH p ORDER BY coalesce(p.version,0) DESC LIMIT 1\n"
            "MATCH (p)-[:CONTAINS_DECISION]->(d:Decision)\n"
            "WITH collect(d) AS D\n"
            "UNWIND D AS m\n"
            "OPTIONAL MATCH (m)<-[r]-(:Decision)\n"
            "WHERE ALL(x IN [startNode(r), endNode(r)] WHERE x:Decision) "
            "AND endNode(r) IN D AND startNode(r) IN D\n"
            "WITH m, count(r) AS indeg\n"
            "RETURN m.id AS id, 'Decision' AS label, toFloat(indeg) AS score\n"
            "ORDER BY score DESC LIMIT $limit"
        )
        recs = self._store.query(q, {"cid": case_id, "limit": limit})
        out: list[CriticalNode] = []
        for r in recs:
            out.append(
                CriticalNode(
                    id=str(r.get("id") or ""),
                    label=str(r.get("label") or "Decision"),
                    score=float(r.get("score") or 0.0),
                )
            )
        return out

    def find_cycles(self, case_id: str, max_depth: int = 6) -> list[PathCycle]:
        q = (
            "MATCH (c:Case {id:$cid})-[:HAS_PLAN]->(p:PlanVersion)\n"
            "WITH p ORDER BY coalesce(p.version,0) DESC LIMIT 1\n"
            "MATCH (p)-[:CONTAINS_DECISION]->(d:Decision)\n"
            "WITH collect(d) AS D\n"
            "UNWIND D AS start\n"
            "MATCH p=(start)-[r*1..$maxDepth]->(start)\n"
            "WHERE ALL(rel IN r WHERE startNode(rel):Decision AND endNode(rel):Decision "
            "AND startNode(rel) IN D AND endNode(rel) IN D)\n"
            "RETURN [x IN nodes(p) | x.id] AS nodes, [rel IN relationships(p) | type(rel)] AS rels\n"
            "LIMIT 20"
        )
        rows = self._store.query(q, {"cid": case_id, "maxDepth": max_depth})
        out: list[PathCycle] = []
        for r in rows:
            nodes = [str(x) for x in (r.get("nodes") or [])]
            rels = [str(x) for x in (r.get("rels") or [])]
            out.append(PathCycle(nodes=nodes, rels=rels))
        return out

    # ---------- Topological layers (Kahn in Python) ----------
    def topo_layers(self, case_id: str) -> LayeredTopology:
        # Pull the node set and edges within the latest plan, then layer them.
        q = (
            "MATCH (c:Case {id:$cid})-[:HAS_PLAN]->(p:PlanVersion)\n"
            "WITH p ORDER BY coalesce(p.version,0) DESC LIMIT 1\n"
            "MATCH (p)-[:CONTAINS_DECISION]->(d:Decision)\n"
            "WITH collect(d) AS D\n"
            "UNWIND D AS d1\n"
            "OPTIONAL MATCH (d1)-[r]->(d2:Decision)\n"
            "WHERE d2 IN D\n"
            "WITH collect(DISTINCT d1.id) AS nodes, collect({src:d1.id, dst:d2.id}) AS edges\n"
            "RETURN nodes, edges"
        )
        rows = self._store.query(q, {"cid": case_id})
        if not rows:
            return LayeredTopology(layers=[])

        nodes: list[str] = [str(x) for x in (rows[0].get("nodes") or [])]
        pairs: list[dict[str, Any]] = [e for e in (rows[0].get("edges") or []) if e.get("dst")]

        # Build indegree and adjacency only within the given node set
        node_set = set(nodes)
        indeg: dict[str, int] = {n: 0 for n in node_set}
        adj: dict[str, list[str]] = defaultdict(list)
        for e in pairs:
            src, dst = str(e.get("src")), str(e.get("dst"))
            if src in node_set and dst in node_set:
                adj[src].append(dst)
                indeg[dst] = indeg.get(dst, 0) + 1
                indeg.setdefault(src, 0)

        # Kahn's algorithm
        layers: list[list[str]] = []
        remaining = set(node_set)
        while remaining:
            layer = [n for n in remaining if indeg.get(n, 0) == 0]
            if not layer:
                # Cycle remainder: output them as the final layer deterministically
                layers.append(sorted(list(remaining)))
                break
            layers.append(sorted(layer))
            for n in layer:
                remaining.remove(n)
                for m in adj.get(n, []):
                    indeg[m] -= 1
        return LayeredTopology(layers=layers)

    # ---------- Placeholder for future metrics ----------
    def agent_metrics(self, agent_id: str, since_iso: str) -> AgentMetrics:  # pragma: no cover (not used yet)
        return AgentMetrics(
            agent_id=agent_id,
            total_runs=0,
            success_rate=0.0,
            p50_duration_ms=0.0,
            p95_duration_ms=0.0,
        )