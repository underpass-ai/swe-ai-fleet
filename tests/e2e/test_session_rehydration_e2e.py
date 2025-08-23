from __future__ import annotations

import json
import time
from typing import Any, cast

import pytest
import redis

from swe_ai_fleet.context.adapters.redis_planning_read_adapter import (
    RedisPlanningReadAdapter,
)
from swe_ai_fleet.context.domain.rehydration_request import RehydrationRequest
from swe_ai_fleet.context.ports.decisiongraph_read_port import (
    DecisionGraphReadPort,
)
from swe_ai_fleet.context.session_rehydration import SessionRehydrationUseCase
from swe_ai_fleet.memory.redis_store import RedisKvPort
from swe_ai_fleet.reports.domain.decision_edges import DecisionEdges
from swe_ai_fleet.reports.domain.decision_node import DecisionNode
from swe_ai_fleet.reports.domain.subtask_node import SubtaskNode
from swe_ai_fleet.reports.dtos.dtos import PlanVersionDTO

pytestmark = pytest.mark.e2e


def _k_spec(case_id: str) -> str:
    return f"swe:case:{case_id}:spec"


def _k_draft(case_id: str) -> str:
    return f"swe:case:{case_id}:planning:draft"


def _k_stream(case_id: str) -> str:
    return f"swe:case:{case_id}:planning:stream"


def _k_summary_last(case_id: str) -> str:
    return f"swe:case:{case_id}:summaries:last"


def _k_handoff_prefix(case_id: str) -> str:
    return f"swe:case:{case_id}:handoff:"


def _cleanup_case(r: redis.Redis, case_id: str) -> None:
    # best-effort cleanup
    keys = [
        _k_spec(case_id),
        _k_draft(case_id),
        _k_stream(case_id),
        _k_summary_last(case_id),
    ]
    # Remove any handoff bundles
    handoff_keys = list(cast(list[str], r.keys(f"{_k_handoff_prefix(case_id)}*")))
    if handoff_keys:
        keys.extend(handoff_keys)
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


def test_session_rehydration_e2e_end_to_end() -> None:
    url = "redis://:swefleet-dev@localhost:6379/0"
    r: redis.Redis = redis.Redis.from_url(url, decode_responses=True)

    case_id = f"e2e-rehydration-{int(time.time())}"
    _cleanup_case(r, case_id)

    # Seed case spec
    spec_doc: dict[str, Any] = {
        "case_id": case_id,
        "title": "E2E Rehydration",
        "description": "End-to-end rehydration context pack",
        "acceptance_criteria": ["context"],
        "constraints": {"env": "prod"},
        "requester_id": "user-1",
        "tags": ["e2e"],
        "created_at_ms": int(time.time() * 1000),
    }
    r.set(_k_spec(case_id), json.dumps(spec_doc))

    # Seed plan draft with two subtasks for different roles
    draft_doc: dict[str, Any] = {
        "plan_id": "P1",
        "case_id": case_id,
        "version": 1,
        "status": "draft",
        "author_id": "bot",
        "rationale": "because",
        "created_at_ms": int(time.time() * 1000),
        "subtasks": [
            {
                "subtask_id": "S1",
                "title": "Implement",
                "description": "Do it",
                "role": "developer",
                "suggested_tech": ["python"],
                "depends_on": [],
                "estimate_points": 3.0,
                "priority": 1,
                "risk_score": 0.2,
                "notes": "",
            },
            {
                "subtask_id": "S2",
                "title": "Test",
                "description": "Verify",
                "role": "qa",
            },
        ],
    }
    r.set(_k_draft(case_id), json.dumps(draft_doc))

    # Seed planning events (ensure chronological ts)
    r.xadd(
        _k_stream(case_id),
        {
            "event": "create_case_spec",
            "actor": "user",
            "payload": json.dumps({}),
            "ts": "1",
        },
    )
    r.xadd(
        _k_stream(case_id),
        {
            "event": "approve_plan",
            "actor": "po",
            "payload": json.dumps({}),
            "ts": "2",
        },
    )

    # Seed last summary
    r.set(_k_summary_last(case_id), "SUMMARY")

    # Build fake graph adapter data
    plan = PlanVersionDTO(
        plan_id="P1",
        case_id=case_id,
        version=1,
        status="approved",
        author_id="bot",
    )
    decisions = [
        DecisionNode(
            id="D1",
            title="Choose DB",
            rationale="Postgres",
            status="accepted",
            created_at_ms=int(time.time() * 1000),
            author_id="arch",
        ),
        DecisionNode(
            id="D2",
            title="Choose Cache",
            rationale="Redis",
            status="open",
            created_at_ms=int(time.time() * 1000),
            author_id="arch",
        ),
    ]
    deps = [DecisionEdges(src_id="D1", rel_type="LEADS_TO", dst_id="D2")]
    impacts = [
        ("D1", SubtaskNode(id="S1", title="Implement", role="developer")),
        ("D2", SubtaskNode(id="S2", title="Test", role="qa")),
    ]

    class _KvShim(RedisKvPort):  # type: ignore[misc]
        def __init__(self, client: redis.Redis) -> None:
            self._c = client

        def get(self, key: str):  # type: ignore[override]
            return self._c.get(key)

        def xrevrange(self, key: str, count: int | None = None):  # type: ignore[override]
            return self._c.xrevrange(key, count=count)

        def pipeline(self):  # type: ignore[override]
            return self._c.pipeline()

    planning_adapter = RedisPlanningReadAdapter(_KvShim(r))
    graph_adapter = _FakeGraphAdapter(plan, decisions, deps, impacts)
    usecase = SessionRehydrationUseCase(planning_adapter, graph_adapter)

    req = RehydrationRequest(
        case_id=case_id,
        roles=["developer", "qa"],
        include_timeline=True,
        include_summaries=True,
        persist_handoff_bundle=True,
        ttl_seconds=60,
    )

    bundle = usecase.build(req)

    # Validate output
    assert bundle.case_id == case_id
    dev_pack = bundle.packs["developer"]
    qa_pack = bundle.packs["qa"]

    assert dev_pack["case_header"]["title"] == "E2E Rehydration"
    assert dev_pack["plan_header"]["plan_id"] == "P1"
    assert dev_pack["last_summary"] == "SUMMARY"
    events_sorted = dev_pack["recent_milestones"]
    assert events_sorted[0]["event"] == "create_case_spec"
    assert events_sorted[-1]["event"] == "approve_plan"

    # Decision relevance by role
    dev_ids = {d["id"] for d in dev_pack["decisions_relevant"]}
    qa_ids = {d["id"] for d in qa_pack["decisions_relevant"]}
    assert "D1" in dev_ids
    assert "D2" in qa_ids

    # Handoff bundle persisted
    handoff_keys = list(cast(list[str], r.keys(f"{_k_handoff_prefix(case_id)}*")))
    assert len(handoff_keys) >= 1
