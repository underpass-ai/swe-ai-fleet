import json
import time
from typing import Any

import pytest
import redis

from swe_ai_fleet.reports.adapters.redis_planning_read_adapter import (
    RedisPlanningReadAdapter,
)
from swe_ai_fleet.reports.domain.report_request import ReportRequest
from swe_ai_fleet.reports.report_usecase import ImplementationReportUseCase

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


def test_report_usecase_e2e_end_to_end():
    url = "redis://:swefleet-dev@localhost:6379/0"
    r: redis.Redis = redis.Redis.from_url(url, decode_responses=True)

    case_id = f"e2e-case-{int(time.time())}"
    _cleanup_case(r, case_id)

    # Seed case spec
    spec_doc: dict[str, Any] = {
        "case_id": case_id,
        "title": "E2E Case",
        "description": "End-to-end report generation",
        "acceptance_criteria": ["works"],
        "constraints": {"env": "prod"},
        "requester_id": "user-1",
        "tags": ["e2e"],
        "created_at_ms": int(time.time() * 1000),
    }
    r.set(_k_spec(case_id), json.dumps(spec_doc))

    # Seed plan draft with one subtask
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
                "role": "dev",
                "suggested_tech": ["python"],
                "depends_on": [],
                "estimate_points": 2.0,
                "priority": 1,
                "risk_score": 0.1,
                "notes": "",
            }
        ],
    }
    r.set(_k_draft(case_id), json.dumps(draft_doc))

    # Seed planning events (newest-first stored by xrevrange; we add in order)
    r.xadd(
        _k_stream(case_id),
        {"event": "created", "actor": "user", "payload": json.dumps({"a": 1}), "ts": "1"},
    )
    r.xadd(
        _k_stream(case_id),
        {"event": "updated", "actor": "user", "payload": json.dumps({"b": 2}), "ts": "2"},
    )

    # Build use case with Redis-backed adapter
    adapter = RedisPlanningReadAdapter(r)
    usecase = ImplementationReportUseCase(adapter)

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
    doc_raw = r.get(_k_report_doc(case_id, last_id))
    assert doc_raw is not None
    doc = json.loads(doc_raw)
    assert doc["case_id"] == case_id

    # Validate content looks correct
    assert report.plan_id == "P1"
    assert "Implementation Report" in report.markdown
    assert f"`{case_id}`" in report.markdown
    assert "Planning Timeline" in report.markdown
