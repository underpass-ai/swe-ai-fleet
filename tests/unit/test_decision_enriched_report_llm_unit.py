from __future__ import annotations

from unittest.mock import MagicMock

from swe_ai_fleet.reports.decision_enriched_report import (
    DecisionEnrichedReportUseCase,
)
from swe_ai_fleet.reports.domain.decision_edges import DecisionEdges
from swe_ai_fleet.reports.domain.decision_node import DecisionNode
from swe_ai_fleet.reports.domain.report_request import ReportRequest
from swe_ai_fleet.reports.domain.subtask_node import SubtaskNode
from swe_ai_fleet.reports.dtos.dtos import CaseSpecDTO
from swe_ai_fleet.reports.ports.decision_graph_read_port import (
    DecisionGraphReadPort,
)


def test_llm_section_included_when_adapter_supports_helpers() -> None:
    r = MagicMock()
    g = MagicMock(spec=DecisionGraphReadPort)

    r.get_case_spec.return_value = CaseSpecDTO(
        case_id="C1", title="t", description="d"
    )
    r.get_plan_draft.return_value = None
    r.get_planning_events.return_value = []
    g.get_plan_by_case.return_value = None
    g.list_decisions.return_value = [
        DecisionNode(id="D", title="t", rationale="r", status="s", created_at_ms=0, author_id="a")
    ]
    g.list_decision_dependencies.return_value = []
    g.list_decision_impacts.return_value = [("D", SubtaskNode(id="S", title="x", role="dev"))]

    # Provide the two helper methods
    r.list_llm_sessions_for_case.return_value = [("SID1", {"role": "dev"})]
    r.get_llm_events_for_session.return_value = [
        {"type": "llm_call", "model": "m", "content": "hello"}
    ]

    uc = DecisionEnrichedReportUseCase(redis_store=r, graph_store=g)
    rep = uc.generate(ReportRequest(case_id="C1", include_timeline=False))
    assert "## LLM Conversations (recent)" in rep.markdown
    # stats augmented
    assert rep.stats.get("llm_sessions", 0) >= 1


