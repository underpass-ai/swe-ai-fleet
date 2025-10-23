from unittest.mock import MagicMock

import pytest

from core.reports.adapters.redis_planning_read_adapter import (
    RedisPlanningReadAdapter,
)
from core.reports.decision_enriched_report import (
    DecisionEnrichedReportUseCase,
)
from core.reports.domain.decision_edges import DecisionEdges
from core.reports.domain.decision_node import DecisionNode
from core.reports.domain.report_request import ReportRequest
from core.reports.domain.subtask_node import SubtaskNode
from core.reports.dtos.dtos import (
    CaseSpecDTO,
    PlanningEventDTO,
    PlanVersionDTO,
    SubtaskPlanDTO,
)
from core.reports.ports.decision_graph_read_port import (
    DecisionGraphReadPort,
)


def _make_spec() -> CaseSpecDTO:
    return CaseSpecDTO(
        case_id="C1",
        title="Feature X",
        description="Deliver feature X",
        acceptance_criteria=["AC1", "AC2"],
        constraints={"budget": "low"},
        requester_id="PO1",
        tags=["t1"],
        created_at_ms=1,
    )


def _make_plan(status: str = "draft") -> PlanVersionDTO:
    s1 = SubtaskPlanDTO(
        subtask_id="S1",
        title="Implement API",
        description="",
        role="dev",
        suggested_tech=["py"],
        depends_on=["S0"],
        estimate_points=5.0,
        priority=1,
        risk_score=0.2,
        notes="",
    )
    s2 = SubtaskPlanDTO(
        subtask_id="S2",
        title="Add tests",
        description="",
        role="qa",
    )
    return PlanVersionDTO(
        plan_id="P1",
        case_id="C1",
        version=3,
        status=status,
        author_id="U2",
        rationale="because",
        subtasks=[s1, s2],
        created_at_ms=2,
    )


def _make_decisions() -> list[DecisionNode]:
    return [
        DecisionNode(
            id="D1",
            title="Choose DB",
            rationale="scalability",
            status="accepted",
            created_at_ms=10,
            author_id="U1",
        ),
        DecisionNode(
            id="D2",
            title="Auth strategy",
            rationale="security",
            status="proposed",
            created_at_ms=20,
            author_id="U2",
        ),
    ]


def _make_edges() -> list[DecisionEdges]:
    return [
        DecisionEdges(src_id="D1", rel_type="DEPENDS_ON", dst_id="D2"),
        DecisionEdges(src_id="D1", rel_type="BLOCKS", dst_id="D3"),
    ]


def _make_impacts() -> list[tuple[str, SubtaskNode]]:
    return [
        ("D1", SubtaskNode(id="S1", title="Implement API", role="dev")),
        ("D1", SubtaskNode(id="S2", title="Add tests", role="qa")),
        ("D2", SubtaskNode(id="S3", title="Docs", role="dev")),
    ]


def _make_events() -> list[PlanningEventDTO]:
    return [
        PlanningEventDTO(
            id="1-0",
            event="create_case_spec",
            actor="po",
            payload={},
            ts_ms=1000,
        ),
        PlanningEventDTO(
            id="2-0",
            event="propose_plan",
            actor="po",
            payload={},
            ts_ms=2000,
        ),
    ]


def _make_redis() -> MagicMock:
    return MagicMock(spec=RedisPlanningReadAdapter)


def _make_graph() -> MagicMock:
    return MagicMock(spec=DecisionGraphReadPort)


def test_generate_happy_path_with_graph_plan_and_persist():
    r = _make_redis()
    g = _make_graph()

    r.get_case_spec.return_value = _make_spec()
    r.get_planning_events.return_value = _make_events()
    r.get_plan_draft.return_value = _make_plan(status="approved")

    g.get_plan_by_case.return_value = _make_plan(status="approved")
    g.list_decisions.return_value = _make_decisions()
    g.list_decision_dependencies.return_value = _make_edges()
    g.list_decision_impacts.return_value = _make_impacts()

    uc = DecisionEnrichedReportUseCase(redis_store=r, graph_store=g)
    req = ReportRequest(case_id="C1", max_events=10, persist_to_redis=True)

    report = uc.generate(req)

    # Interactions
    r.get_case_spec.assert_called_once_with("C1")
    g.get_plan_by_case.assert_called_once_with("C1")
    g.list_decisions.assert_called_once_with("C1")
    g.list_decision_dependencies.assert_called_once_with("C1")
    g.list_decision_impacts.assert_called_once_with("C1")
    r.get_planning_events.assert_called_once_with("C1", count=10)
    assert r.save_report.call_count == 1

    # Stats
    assert report.stats["decisions"] == 2
    assert report.stats["decision_edges"] == 2
    assert report.stats["impacted_subtasks"] == 3
    assert report.stats["plan_status"] == "approved"
    assert report.stats["events"] == 2
    assert report.stats["max_dependencies_on_one_decision"] == 2
    assert report.stats["max_impacts_from_one_decision"] == 2

    # Markdown key sections
    md = report.markdown
    assert "## Decisions (ordered)" in md
    assert "## Decision Dependency Map" in md
    assert "## Decision → Subtask Impact" in md
    assert "## Subtasks (from planning draft)" in md
    assert "## Milestones & Timeline" in md
    assert "## Next Steps" in md


def test_generate_uses_redis_plan_when_graph_missing():
    r = _make_redis()
    g = _make_graph()

    r.get_case_spec.return_value = _make_spec()
    r.get_plan_draft.return_value = _make_plan(status="draft")
    r.get_planning_events.return_value = []

    g.get_plan_by_case.return_value = None
    g.list_decisions.return_value = []
    g.list_decision_dependencies.return_value = []
    g.list_decision_impacts.return_value = []

    uc = DecisionEnrichedReportUseCase(redis_store=r, graph_store=g)
    req = ReportRequest(case_id="C1", include_timeline=False)

    report = uc.generate(req)
    assert report.plan_id == "P1"
    assert report.stats["plan_status"] == "draft"
    md = report.markdown
    assert "Plan ID" in md and "P1" in md
    assert "## Milestones & Timeline" not in md


def test_generate_missing_spec_raises():
    r = _make_redis()
    g = _make_graph()
    r.get_case_spec.return_value = None

    uc = DecisionEnrichedReportUseCase(redis_store=r, graph_store=g)
    with pytest.raises(ValueError, match="Case spec not found"):
        uc.generate(ReportRequest(case_id="C1"))


def test_generate_does_not_persist_when_disabled():
    r = _make_redis()
    g = _make_graph()

    r.get_case_spec.return_value = _make_spec()
    r.get_plan_draft.return_value = _make_plan(status="draft")
    r.get_planning_events.return_value = []

    g.get_plan_by_case.return_value = None
    g.list_decisions.return_value = []
    g.list_decision_dependencies.return_value = []
    g.list_decision_impacts.return_value = []

    uc = DecisionEnrichedReportUseCase(redis_store=r, graph_store=g)
    uc.generate(ReportRequest(case_id="C1", persist_to_redis=False))
    r.save_report.assert_not_called()
