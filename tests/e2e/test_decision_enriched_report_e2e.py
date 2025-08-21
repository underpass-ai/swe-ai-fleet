from __future__ import annotations

import json
import time
from typing import Any

import pytest
import redis

from swe_ai_fleet.reports.adapters.redis_planning_read_adapter import (
    RedisPlanningReadAdapter,
)
from swe_ai_fleet.reports.decision_enriched_report import (
    DecisionEnrichedReportUseCase,
)
from swe_ai_fleet.reports.domain.decision_edges import DecisionEdges
from swe_ai_fleet.reports.domain.decision_node import DecisionNode
from swe_ai_fleet.reports.domain.report_request import ReportRequest
from swe_ai_fleet.reports.domain.subtask_node import SubtaskNode
from swe_ai_fleet.reports.dtos.dtos import PlanVersionDTO
from swe_ai_fleet.reports.ports.decision_graph_read_port import (
    DecisionGraphReadPort,
)

pytestmark = pytest.mark.e2e


def _k_spec(case_id: str) -> str:
    return f"swe:case:{case_id}:spec"


def _k_draft(case_id: str) -> str:
    return f"swe:case:{case_id}:planning:draft"


def _k_stream(case_id: str) -> str:
    return f"swe:case:{case_id}:planning:stream"


def _k_report_list(case_id: str) -> str:
    return f"swe:case:{case_id}:reports:implementation:ids"


def _k_report_doc(case_id: str, report_id: str) -> str:
    return f"swe:case:{case_id}:reports:implementation:{report_id}"


def _k_report_last(case_id: str) -> str:
    return f"swe:case:{case_id}:reports:implementation:last"


def _cleanup_case(r: redis.Redis, case_id: str) -> None:
    # best-effort cleanup
    keys = [
        _k_spec(case_id),
        _k_draft(case_id),
        _k_stream(case_id),
        _k_report_list(case_id),
        _k_report_last(case_id),
    ]
    r.delete(*keys)


class _FakeGraphAdapter(DecisionGraphReadPort):
    def __init__(
        self,
        plan: PlanVersionDTO | None,
        decisions: list[DecisionNode],
        deps: list[DecisionEdges],
        impacts: list[tuple[str, SubtaskNode]],
    ) -> None:
        self._plan = plan
        self._decisions = decisions
        self._deps = deps
        self._impacts = impacts

    def get_plan_by_case(self, case_id: str) -> PlanVersionDTO | None:
        return self._plan

    def list_decisions(self, case_id: str) -> list[DecisionNode]:
        return self._decisions

    def list_decision_dependencies(self, case_id: str) -> list[DecisionEdges]:
        return self._deps

    def list_decision_impacts(self, case_id: str) -> list[tuple[str, SubtaskNode]]:
        return self._impacts


def test_decision_enriched_report_e2e_end_to_end() -> None:
    url = "redis://:swefleet-dev@localhost:6379/0"
    r: redis.Redis = redis.Redis.from_url(url, decode_responses=True)

    case_id = f"e2e-decision-enriched-{int(time.time())}"
    _cleanup_case(r, case_id)

    # Seed case spec
    spec_doc: dict[str, Any] = {
        "case_id": case_id,
        "title": "E2E Decision-Enriched",
        "description": "End-to-end decision-enriched report",
        "acceptance_criteria": ["renders"],
        "constraints": {"env": "prod"},
        "requester_id": "user-1",
        "tags": ["e2e"],
        "created_at_ms": int(time.time() * 1000),
    }
    r.set(_k_spec(case_id), json.dumps(spec_doc))

    # Seed plan draft with one subtask (used for optional subtasks table)
    draft_doc: dict[str, Any] = {
        "plan_id": "P1",
        "case_id": case_id,
        "version": 2,
        "status": "draft",
        "author_id": "bot",
        "rationale": "because",
        "created_at_ms": int(time.time() * 1000),
        "subtasks": [
            {
                "subtask_id": "S1",
                "title": "Implement",
                "description": "Do it",
                "role": "dev",
                "suggested_tech": ["python"],
                "depends_on": [],
                "estimate_points": 3.0,
                "priority": 1,
                "risk_score": 0.2,
                "notes": "",
            }
        ],
    }
    r.set(_k_draft(case_id), json.dumps(draft_doc))

    # Seed planning events (newest-first stored by xrevrange; we add in order)
    r.xadd(
        _k_stream(case_id),
        {"event": "create_case_spec", "actor": "user", "payload": "{}", "ts": "1"},
    )
    r.xadd(
        _k_stream(case_id),
        {"event": "propose_plan", "actor": "bot", "payload": "{}", "ts": "2"},
    )

    # Build fake graph adapter data
    plan = PlanVersionDTO(
        plan_id="P1",
        case_id=case_id,
        version=2,
        status="draft",
        author_id="bot",
    )
    decisions = [
        DecisionNode(
            id="D1",
            title="Choose DB",
            rationale="Postgres is fine",
            status="accepted",
            created_at_ms=int(time.time() * 1000),
            author_id="arch",
        )
    ]
    deps = [DecisionEdges(src_id="D1", rel_type="GOVERNS", dst_id="D2")]
    impacts = [("D1", SubtaskNode(id="S1", title="Implement", role="dev"))]

    # Build use case with Redis-backed adapter and fake graph adapter
    # Minimal KV port shim over redis-py client
    class _KvShim:
        def __init__(self, client: redis.Redis):
            self._c = client

        def get(self, key: str) -> str | None:
            return self._c.get(key)

        def xrevrange(self, key: str, count: int | None = None):
            return self._c.xrevrange(key, count=count)

        def pipeline(self):
            return self._c.pipeline()

    redis_adapter = RedisPlanningReadAdapter(_KvShim(r))
    graph_adapter = _FakeGraphAdapter(plan, decisions, deps, impacts)
    usecase = DecisionEnrichedReportUseCase(redis_adapter, graph_adapter)

    req = ReportRequest(
        case_id=case_id,
        include_constraints=True,
        include_acceptance=True,
        include_timeline=True,
        include_dependencies=True,
        persist_to_redis=True,
        ttl_seconds=120,
    )

    report = usecase.generate(req)

    # Validate persistence
    last_id = r.get(_k_report_last(case_id))
    assert last_id is not None
    doc_raw = r.get(_k_report_doc(case_id, str(last_id)))
    assert doc_raw is not None
    doc = json.loads(doc_raw)
    assert doc["case_id"] == case_id

    # Validate content and stats look correct
    assert "Implementation Report (Graph-guided)" in report.markdown
    assert f"`{case_id}`" in report.markdown
    assert "## Decisions (ordered)" in report.markdown
    assert "## Decision Dependency Map" in report.markdown
    assert "## Decision → Subtask Impact" in report.markdown
    assert report.plan_id == "P1"
    assert report.stats["decisions"] == len(decisions)
    assert report.stats["decision_edges"] == len(deps)
    assert report.stats["impacted_subtasks"] == len(impacts)
    assert report.stats["plan_status"] == plan.status
