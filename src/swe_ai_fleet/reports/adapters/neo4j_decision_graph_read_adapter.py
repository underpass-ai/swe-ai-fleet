from swe_ai_fleet.context.adapters.neo4j_query_store import Neo4jQueryStore
from swe_ai_fleet.reports.domain.decision_edges import DecisionEdges
from swe_ai_fleet.reports.domain.decision_node import DecisionNode
from swe_ai_fleet.reports.domain.subtask_node import SubtaskNode
from swe_ai_fleet.reports.dtos.dtos import PlanVersionDTO
from swe_ai_fleet.reports.ports.decision_graph_read_port import (
    DecisionGraphReadPort,
)


class Neo4jDecisionGraphReadAdapter(DecisionGraphReadPort):
    """
    Read-only adapter using a thin `Neo4jStore` wrapper.
    Assumes the knowledge graph already projected:
      (:Case {id})-[:HAS_PLAN]->(:PlanVersion {id, version, status})
      (:PlanVersion)-[:CONTAINS_DECISION]->(:Decision {
        id, title, rationale, status, created_at_ms, author_id?
      })
      (:Decision)-[:AUTHORED_BY]->(:Actor {id})
      (:Subtask)-[:INFLUENCED_BY]->(:Decision)
      (Decision)-[REL]->(Decision)
      with types like DEPENDS_ON, GOVERNS, etc.
    """

    def __init__(self, store: Neo4jQueryStore) -> None:
        self._store = store

    def close(self) -> None:
        # The store API does not expose close semantics; no-op for symmetry.
        return None

    def get_plan_by_case(self, case_id: str) -> PlanVersionDTO | None:
        q = (
            "MATCH (c:Case {id:$cid})-[:HAS_PLAN]->(p:PlanVersion)\n"
            "RETURN p.id AS plan_id, p.case_id AS case_id,\n"
            "       p.version AS version, p.status AS status,\n"
            "       p.author_id AS author_id, p.rationale AS rationale,\n"
            "       p.created_at_ms AS created_at_ms\n"
            "ORDER BY coalesce(p.version,0) DESC\n"
            "LIMIT 1"
        )
        recs = self._store.query(q, {"cid": case_id})
        if not recs:
            return None
        rec = recs[0]
        return PlanVersionDTO(
            plan_id=rec["plan_id"],
            case_id=rec.get("case_id") or case_id,
            version=int(rec.get("version") or 0),
            status=str(rec.get("status") or "UNKNOWN"),
            author_id=str(rec.get("author_id") or "unknown"),
            rationale=str(rec.get("rationale") or ""),
            subtasks=[],  # not needed here; impacts are queried separately
            created_at_ms=int(rec.get("created_at_ms") or 0),
        )

    def list_decisions(self, case_id: str) -> list[DecisionNode]:
        q = (
            "MATCH (c:Case {id:$cid})-[:HAS_PLAN]->(:PlanVersion)\n"
            "-[:CONTAINS_DECISION]->(d:Decision)\n"
            "OPTIONAL MATCH (d)-[:AUTHORED_BY]->(a:Actor)\n"
            "RETURN d.id AS id, d.title AS title, d.rationale AS rationale,\n"
            "       d.status AS status,\n"
            "       coalesce(d.created_at_ms,0) AS created_at_ms,\n"
            "       coalesce(d.author_id, a.id, 'unknown') AS author_id\n"
            "ORDER BY created_at_ms ASC, id ASC"
        )
        return [
            DecisionNode(
                id=str(r["id"]),
                title=str(r.get("title") or ""),
                rationale=str(r.get("rationale") or ""),
                status=str(r.get("status") or "PROPOSED"),
                created_at_ms=int(r.get("created_at_ms") or 0),
                author_id=str(r.get("author_id") or "unknown"),
            )
            for r in self._store.query(q, {"cid": case_id})
        ]

    def list_decision_dependencies(self, case_id: str) -> list[DecisionEdges]:
        q = (
            "MATCH (c:Case {id:$cid})-[:HAS_PLAN]->(:PlanVersion)\n"
            "-[:CONTAINS_DECISION]->(d1:Decision)\n"
            "MATCH (d1)-[r]->(d2:Decision)\n"
            "WHERE type(r) IS NOT NULL\n"
            "RETURN d1.id AS src,\n"
            "       type(r) AS rel,\n"
            "       d2.id AS dst"
        )
        return [
            DecisionEdges(
                src_id=str(r["src"]),
                rel_type=str(r["rel"]),
                dst_id=str(r["dst"]),
            )
            for r in self._store.query(q, {"cid": case_id})
        ]

    type SubtaskImpact = tuple[str, SubtaskNode]

    def list_decision_impacts(self, case_id: str) -> list[SubtaskImpact]:
        q = (
            "MATCH (c:Case {id:$cid})-[:HAS_PLAN]->(:PlanVersion)\n"
            "-[:CONTAINS_DECISION]->(d:Decision)\n"
            "MATCH (s:Subtask)-[:INFLUENCED_BY]->(d)\n"
            "RETURN d.id AS did, s.id AS sid,\n"
            "       s.title AS stitle,\n"
            "       s.role AS srole\n"
            "ORDER BY did, sid"
        )
        out: list[tuple[str, SubtaskNode]] = []
        for r in self._store.query(q, {"cid": case_id}):
            out.append(
                (
                    str(r["did"]),
                    SubtaskNode(
                        id=str(r["sid"]),
                        title=str(r.get("stitle") or ""),
                        role=str(r.get("srole") or ""),
                    ),
                )
            )
        return out
