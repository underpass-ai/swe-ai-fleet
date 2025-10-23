from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any

SessionRehydrationUseCase = import_module(
    "core.context.session_rehydration"
).SessionRehydrationUseCase
RehydrationRequest = import_module("core.context.domain.rehydration_request").RehydrationRequest
DecisionEdges = import_module("core.reports.domain.decision_edges").DecisionEdges
DecisionNode = import_module("core.reports.domain.decision_node").DecisionNode
SubtaskNode = import_module("core.reports.domain.subtask_node").SubtaskNode
_dtos_mod = import_module("core.reports.dtos.dtos")
CaseSpecDTO = _dtos_mod.CaseSpecDTO
PlanVersionDTO = _dtos_mod.PlanVersionDTO
PlanningEventDTO = _dtos_mod.PlanningEventDTO
SubtaskPlanDTO = _dtos_mod.SubtaskPlanDTO


@dataclass
class _PlanningStoreFake:
    spec: Any
    plan: Any
    events: list[Any]
    last_summary: str | None = None
    saved_bundle: dict[str, Any] | None = None
    saved_ttl: int | None = None

    def get_case_spec(self, _case_id: str) -> Any:  # type: ignore[override]
        return self.spec

    def get_plan_draft(self, _case_id: str) -> Any:  # type: ignore[override]
        return self.plan

    def get_planning_events(
        self,
        _case_id: str,
        count: int = 200,
    ) -> list[Any]:  # type: ignore[override]
        return list(self.events)[:count]

    # optional APIs used behind hasattr checks
    def read_last_summary(self, _case_id: str) -> str | None:
        return self.last_summary

    def save_handoff_bundle(self, _case_id: str, bundle: dict[str, Any], ttl_seconds: int) -> None:
        self.saved_bundle = bundle
        self.saved_ttl = ttl_seconds


@dataclass
class _GraphStoreFake:
    plan: Any
    decisions: list[Any]
    edges: list[Any]
    impacts: list[tuple[str, Any]]

    def get_plan_by_case(self, _case_id: str) -> Any:  # type: ignore[override]
        return self.plan

    def list_decisions(self, _case_id: str) -> list[Any]:  # type: ignore[override]
        return self.decisions

    def list_decision_dependencies(self, _case_id: str) -> list[Any]:  # type: ignore[override]
        return self.edges

    def list_decision_impacts(self, _case_id: str) -> list[tuple[str, Any]]:  # type: ignore[override]
        return self.impacts


def _mk_sample_data():
    spec = CaseSpecDTO(
        case_id="C1",
        title="Case Title",
        description="desc",
        acceptance_criteria=["a"],
        constraints={"budget": "low"},
        requester_id="u1",
        tags=["t"],
        created_at_ms=1,
    )
    plan_g = PlanVersionDTO(
        plan_id="P1",
        case_id="C1",
        version=2,
        status="APPROVED",
        author_id="u2",
        rationale="because",
        subtasks=[],
        created_at_ms=2,
    )
    plan_r = PlanVersionDTO(
        plan_id="P_DRAFT",
        case_id="C1",
        version=3,
        status="DRAFT",
        author_id="u3",
        rationale="draft",
        subtasks=[
            SubtaskPlanDTO(
                subtask_id="S1",
                title="Implement X",
                description="",
                role="developer",
                suggested_tech=["py"],
                depends_on=[],
                estimate_points=3.0,
                priority=1,
                risk_score=0.1,
                notes="",
            ),
            SubtaskPlanDTO(
                subtask_id="S2",
                title="Test X",
                description="",
                role="qa",
            ),
        ],
        created_at_ms=10,
    )
    decisions = [
        DecisionNode(
            id="D1",
            title="Pick DB",
            rationale="r",
            status="done",
            author_id="a",
            created_at_ms=5,
        ),
        DecisionNode(
            id="D2",
            title="Pick Cache",
            rationale="r",
            status="open",
            author_id="a",
            created_at_ms=6,
        ),
    ]
    edges = [DecisionEdges(src_id="D1", rel_type="leads_to", dst_id="D2")]
    impacts = [
        ("D1", SubtaskNode(id="S1", title="Implement X", role="developer")),
        ("D2", SubtaskNode(id="S3", title="Infra", role="devops")),
    ]
    events = [
        PlanningEventDTO(
            id="1-0",
            event="create_case_spec",
            actor="sys",
            payload={},
            ts_ms=2,
        ),
        PlanningEventDTO(
            id="1-1",
            event="noise_event",
            actor="sys",
            payload={},
            ts_ms=3,
        ),
        PlanningEventDTO(
            id="1-2",
            event="approve_plan",
            actor="po",
            payload={},
            ts_ms=4,
        ),
    ]
    return spec, plan_g, plan_r, decisions, edges, impacts, events


def test_rehydration_builds_role_packs_and_stats():
    spec, plan_g, plan_r, decisions, edges, impacts, events = _mk_sample_data()
    planning = _PlanningStoreFake(
        spec=spec,
        plan=plan_r,
        events=events,
        last_summary="SUM",
    )
    graph = _GraphStoreFake(
        plan=plan_g,
        decisions=decisions,
        edges=edges,
        impacts=impacts,
    )

    uc = SessionRehydrationUseCase(planning_store=planning, graph_store=graph)
    req = RehydrationRequest(case_id="C1", roles=["developer"], include_timeline=True)

    out = uc.build(req)

    assert out.case_id == "C1"
    assert out.stats["decisions"] == len(decisions)
    assert out.stats["decision_edges"] == len(edges)
    assert out.stats["events"] == len(events)

    dev_pack = out.packs["developer"]
    assert dev_pack["case_header"]["title"] == spec.title
    assert dev_pack["plan_header"]["status"] == plan_g.status
    # Relevant decision should include D1 due to impact on S1 (developer)
    ids = {d["id"] for d in dev_pack["decisions_relevant"]}
    assert "D1" in ids
    # Impacted subtasks filtered by developer role
    assert any(im["subtask_id"] == "S1" for im in dev_pack["impacted_subtasks"])
    # Timeline milestones filtered and sorted
    events_sorted = dev_pack["recent_milestones"]
    assert events_sorted[0]["event"] == "create_case_spec"
    assert events_sorted[-1]["event"] == "approve_plan"
    # Summary included
    assert dev_pack["last_summary"] == "SUM"


def test_rehydration_fallback_to_first_decisions_and_persist_handoff():
    spec, plan_g, plan_r, decisions, edges, impacts, events = _mk_sample_data()
    # remove impacts for QA so fallback path is taken
    impacts = [(did, sub) for (did, sub) in impacts if sub.role != "qa"]
    planning = _PlanningStoreFake(spec=spec, plan=plan_r, events=events, last_summary=None)
    graph = _GraphStoreFake(plan=plan_g, decisions=decisions, edges=edges, impacts=impacts)

    uc = SessionRehydrationUseCase(planning_store=planning, graph_store=graph)
    req = RehydrationRequest(
        case_id="C1",
        roles=["qa"],
        include_timeline=False,
        include_summaries=False,
        persist_handoff_bundle=True,
        ttl_seconds=123,
    )

    out = uc.build(req)
    qa_pack = out.packs["qa"]
    # No timeline included
    assert qa_pack["recent_milestones"] == []
    # No summary included
    assert qa_pack["last_summary"] is None
    # Fallback uses first decisions if no relevant ones found
    assert len(qa_pack["decisions_relevant"]) == min(5, len(decisions))
    # Persist triggered with ttl
    assert planning.saved_bundle is not None
    assert planning.saved_ttl == 123
