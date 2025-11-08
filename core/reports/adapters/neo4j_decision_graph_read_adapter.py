from core.context.adapters.neo4j_query_store import Neo4jQueryStore
from core.context.domain.decision_status import DecisionStatus
from core.context.domain.entity_ids.actor_id import ActorId
from core.context.domain.entity_ids.decision_id import DecisionId
from core.context.domain.entity_ids.task_id import TaskId
from core.context.domain.epic import Epic
from core.context.domain.graph_relation_type import GraphRelationType
from core.context.domain.neo4j_queries import Neo4jQuery
from core.context.domain.role import Role
from core.context.infrastructure.mappers.epic_mapper import EpicMapper
from core.reports.domain.decision_edges import DecisionEdges
from core.reports.domain.decision_node import DecisionNode
from core.reports.domain.task_node import TaskNode
from core.reports.dtos.dtos import PlanVersionDTO
from core.reports.ports.decision_graph_read_port import (
    DecisionGraphReadPort,
)


class Neo4jDecisionGraphReadAdapter(DecisionGraphReadPort):
    """
    Read-only adapter using a thin `Neo4jStore` wrapper.
    Assumes the knowledge graph already projected:
      (:Epic {epic_id, title, description, status})-[:CONTAINS_STORY]->(:Story {story_id, name})
      (:Story)-[:HAS_PLAN]->(:PlanVersion {id, version, status})
      (:PlanVersion)-[:CONTAINS_DECISION]->(:Decision {
        id, title, rationale, status, created_at_ms, author_id?
      })
      (:Decision)-[:AUTHORED_BY]->(:Actor {id})
      (:Task)-[:INFLUENCED_BY]->(:Decision)
      (Decision)-[REL]->(Decision)
      with types like DEPENDS_ON, GOVERNS, etc.
    """

    def __init__(self, store: Neo4jQueryStore) -> None:
        self._store = store

    def close(self) -> None:
        # The store API does not expose close semantics; no-op for symmetry.
        return None

    def get_epic_by_story(self, story_id: str) -> Epic:
        """Get the Epic that contains this Story.

        DOMAIN INVARIANT: Every story MUST have an epic.

        Args:
            story_id: Story identifier

        Returns:
            Epic entity (NEVER None - fail-fast if not found)

        Raises:
            ValueError: If epic not found (violates domain invariant)
        """
        recs = self._store.query(Neo4jQuery.GET_EPIC_BY_STORY.value, {"story_id": story_id})

        if not recs:
            raise ValueError(
                f"Epic not found for story {story_id}. "
                f"Domain invariant violation: Every story must belong to an epic."
            )

        rec = recs[0]

        # Use EpicMapper to convert Neo4j record to Epic entity
        return EpicMapper.from_neo4j_node(rec)

    def get_plan_by_case(self, case_id: str) -> PlanVersionDTO | None:
        # Use centralized query (supports both Story and legacy Case)
        recs = self._store.query(Neo4jQuery.GET_PLAN_BY_STORY.value, {"story_id": case_id})
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
        # Use centralized query (supports both story_id and legacy case_id)
        results = []
        for r in self._store.query(Neo4jQuery.LIST_DECISIONS_BY_STORY.value, {"story_id": case_id}):
            # Parse status string to DecisionStatus enum (fail-fast if invalid)
            status_str = str(r.get("status") or "PROPOSED")
            try:
                status_enum = DecisionStatus(status_str)
            except ValueError as e:
                raise ValueError(
                    f"Invalid decision status '{status_str}' for decision {r['id']}. "
                    f"Must be one of: {[s.value for s in DecisionStatus]}"
                ) from e

            results.append(
                DecisionNode(
                    id=DecisionId(value=str(r["id"])),
                    title=str(r.get("title") or ""),
                    rationale=str(r.get("rationale") or ""),
                    status=status_enum,
                    created_at_ms=int(r.get("created_at_ms") or 0),
                    author_id=ActorId(value=str(r.get("author_id") or "unknown")),
                )
            )
        return results

    def list_decision_dependencies(self, case_id: str) -> list[DecisionEdges]:
        results = []
        for r in self._store.query(Neo4jQuery.LIST_DECISION_DEPENDENCIES.value, {"story_id": case_id}):
            # Parse relation type string to GraphRelationType enum (fail-fast if invalid)
            rel_type_str = str(r["rel"])
            try:
                rel_type_enum = GraphRelationType(rel_type_str)
            except ValueError as e:
                raise ValueError(
                    f"Invalid relation type '{rel_type_str}' for edge {r['src']}->{r['dst']}. "
                    f"Must be one of: {[rt.value for rt in GraphRelationType]}"
                ) from e

            results.append(
                DecisionEdges(
                    src_id=DecisionId(value=str(r["src"])),
                    rel_type=rel_type_enum,
                    dst_id=DecisionId(value=str(r["dst"])),
                )
            )
        return results

    type TaskImpact = tuple[str, TaskNode]

    def list_decision_impacts(self, case_id: str) -> list[TaskImpact]:
        out: list[tuple[str, TaskNode]] = []
        for r in self._store.query(Neo4jQuery.LIST_DECISION_IMPACTS.value, {"story_id": case_id}):
            # Parse role string to Role enum (fail-fast if invalid)
            role_str = str(r.get("trole") or "")
            try:
                role_enum = Role(role_str) if role_str else Role.DEVELOPER  # Default
            except ValueError as e:
                raise ValueError(
                    f"Invalid role '{role_str}' for task {r['tid']}. "
                    f"Must be one of: {[r.value for r in Role]}"
                ) from e

            out.append(
                (
                    str(r["did"]),
                    TaskNode(
                        id=TaskId(value=str(r["tid"])),
                        title=str(r.get("ttitle") or ""),
                        role=role_enum,
                    ),
                )
            )
        return out
