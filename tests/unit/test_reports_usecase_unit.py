from unittest.mock import MagicMock

import pytest

from swe_ai_fleet.reports.domain.report_request import ReportRequest
from swe_ai_fleet.reports.dtos.dtos import (
    CaseSpecDTO,
    PlanningEventDTO,
    PlanVersionDTO,
    SubtaskPlanDTO,
)
from swe_ai_fleet.reports.ports.planning_read_port import PlanningReadPort
from swe_ai_fleet.reports.report_usecase import ImplementationReportUseCase


def _make_spec() -> CaseSpecDTO:
    return CaseSpecDTO(
        case_id="C1",
        title="Title",
        description="Desc",
        acceptance_criteria=["AC1"],
        constraints={"k": "v"},
        requester_id="U1",
        tags=["t1"],
        created_at_ms=1,
    )


def _make_plan() -> PlanVersionDTO:
    s1 = SubtaskPlanDTO(
        subtask_id="S1",
        title="T1",
        description="D1",
        role="dev",
        suggested_tech=["py"],
        depends_on=["S0"],
        estimate_points=3.0,
        priority=1,
        risk_score=0.1,
        notes="",
    )
    s2 = SubtaskPlanDTO(
        subtask_id="S2",
        title="T2",
        description="D2",
        role="qa",
    )
    return PlanVersionDTO(
        plan_id="P1",
        case_id="C1",
        version=1,
        status="draft",
        author_id="U2",
        rationale="because",
        subtasks=[s1, s2],
        created_at_ms=2,
    )


def _make_events() -> list[PlanningEventDTO]:
    return [
        PlanningEventDTO(
            id="1-0",
            event="created",
            actor="u",
            payload={"a": 1},
            ts_ms=1,
        ),
        PlanningEventDTO(
            id="2-0",
            event="updated",
            actor="u",
            payload={"b": 2},
            ts_ms=2,
        ),
    ]


def _make_store() -> MagicMock:
    return MagicMock(spec=PlanningReadPort)


def test_generate_happy_path_persists_and_renders():
    store = _make_store()
    store.get_case_spec.return_value = _make_spec()
    store.get_plan_draft.return_value = _make_plan()
    store.get_planning_events.return_value = _make_events()

    uc = ImplementationReportUseCase(store)
    req = ReportRequest(
        case_id="C1",
        max_events=5,
        include_constraints=True,
        include_acceptance=True,
        include_timeline=True,
        include_dependencies=True,
        persist_to_redis=True,
        ttl_seconds=60,
    )

    report = uc.generate(req)

    # store interactions
    store.get_case_spec.assert_called_once_with("C1")
    store.get_plan_draft.assert_called_once_with("C1")
    store.get_planning_events.assert_called_once_with("C1", count=5)
    assert store.save_report.call_count == 1
    args, kwargs = store.save_report.call_args
    assert args[0] == "C1"
    assert kwargs["ttl_seconds"] == 60 if "ttl_seconds" in kwargs else args[2] == 60

    # stats
    assert report.stats["total_subtasks"] == 2
    assert report.stats["dependencies"] == 1
    assert report.stats["roles"] == {"dev": 1, "qa": 1}
    assert report.stats["events"] == 2

    # markdown key sections
    md = report.markdown
    assert "# Implementation Report" in md
    assert "Case ID:" in md and "`C1`" in md
    assert "Plan ID:" in md and "`P1`" in md
    assert "Generated at:" in md
    assert "## Overview" in md and "Desc" in md
    assert "### Constraints" in md and "k:" in md
    assert "## Acceptance Criteria" in md and "AC1" in md
    assert "## Subtasks" in md and "`S1`" in md
    assert "## Planning Timeline" in md and "created" in md
    assert "## Next Steps" in md


def test_generate_skips_timeline_when_disabled():
    store = _make_store()
    store.get_case_spec.return_value = _make_spec()
    store.get_plan_draft.return_value = _make_plan()

    uc = ImplementationReportUseCase(store)
    req = ReportRequest(case_id="C1", include_timeline=False)

    report = uc.generate(req)
    store.get_planning_events.assert_not_called()
    assert report.stats["events"] == 0


def test_generate_missing_spec_raises():
    store = _make_store()
    store.get_case_spec.return_value = None
    store.get_plan_draft.return_value = _make_plan()

    uc = ImplementationReportUseCase(store)
    req = ReportRequest(case_id="C1")

    with pytest.raises(ValueError, match="Case spec not found"):
        uc.generate(req)


def test_generate_missing_plan_raises():
    store = _make_store()
    store.get_case_spec.return_value = _make_spec()
    store.get_plan_draft.return_value = None

    uc = ImplementationReportUseCase(store)
    req = ReportRequest(case_id="C1")

    with pytest.raises(ValueError, match="Plan draft not found"):
        uc.generate(req)


def test_generate_does_not_persist_when_disabled():
    store = _make_store()
    store.get_case_spec.return_value = _make_spec()
    store.get_plan_draft.return_value = _make_plan()
    store.get_planning_events.return_value = []

    uc = ImplementationReportUseCase(store)
    req = ReportRequest(case_id="C1", persist_to_redis=False)

    uc.generate(req)
    store.save_report.assert_not_called()
