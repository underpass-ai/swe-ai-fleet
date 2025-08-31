import json
import time
from typing import Any
from unittest.mock import MagicMock

import pytest
import redis

from swe_ai_fleet.reports.adapters.redis_planning_read_adapter import (
    RedisPlanningReadAdapter,
)
from swe_ai_fleet.reports.domain.report_request import ReportRequest
from swe_ai_fleet.reports.report_usecase import ImplementationReportUseCase

# Mock analytics types for testing
try:
    from swe_ai_fleet.reports.domain.graph_analytics_types import (
        CriticalNode,
        LayeredTopology,
        PathCycle,
    )
except ImportError:
    # Fallback for environments without analytics types
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class CriticalNode:
        id: str
        label: str
        score: float

    @dataclass(frozen=True)
    class PathCycle:
        nodes: list[str]
        rels: list[str]

    @dataclass(frozen=True)
    class LayeredTopology:
        layers: list[list[str]]

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


def _make_analytics_port() -> MagicMock:
    """Create a mock analytics port for testing."""
    analytics_port = MagicMock()
    analytics_port.get_critical_decisions.return_value = [
        CriticalNode(id="D1", label="Decision", score=5.0),
        CriticalNode(id="D2", label="Decision", score=3.0),
    ]
    analytics_port.find_cycles.return_value = [
        PathCycle(nodes=["D1", "D2", "D1"], rels=["DEPENDS_ON", "BLOCKS"]),
    ]
    analytics_port.topo_layers.return_value = LayeredTopology(
        layers=[["D1"], ["D2", "D3"], ["D4"]]
    )
    return analytics_port


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

    # Validate no analytics section when analytics port is not provided
    assert "Graph Analytics (Decisions)" not in report.markdown
    assert "Critical Decisions (by indegree)" not in report.markdown
    assert "Cycles" not in report.markdown
    assert "Topological Layers" not in report.markdown


def test_report_usecase_e2e_with_analytics():
    url = "redis://:swefleet-dev@localhost:6379/0"
    r: redis.Redis = redis.Redis.from_url(url, decode_responses=True)

    case_id = f"e2e-analytics-{int(time.time())}"
    _cleanup_case(r, case_id)

    # Seed case spec
    spec_doc: dict[str, Any] = {
        "case_id": case_id,
        "title": "E2E Analytics Case",
        "description": "End-to-end report generation with analytics",
        "acceptance_criteria": ["works with analytics"],
        "constraints": {"env": "prod"},
        "requester_id": "user-1",
        "tags": ["e2e", "analytics"],
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
        "rationale": "because analytics",
        "created_at_ms": int(time.time() * 1000),
        "subtasks": [
            {
                "subtask_id": "S1",
                "title": "Implement Analytics",
                "description": "Do analytics",
                "role": "dev",
                "suggested_tech": ["python", "neo4j"],
                "depends_on": [],
                "estimate_points": 3.0,
                "priority": 1,
                "risk_score": 0.2,
                "notes": "analytics integration",
            }
        ],
    }
    r.set(_k_draft(case_id), json.dumps(draft_doc))

    # Seed planning events
    r.xadd(
        _k_stream(case_id),
        {"event": "created", "actor": "user", "payload": json.dumps({"analytics": True}), "ts": "1"},
    )

    # Build use case with Redis-backed adapter and analytics port
    adapter = RedisPlanningReadAdapter(r)
    analytics_port = _make_analytics_port()
    usecase = ImplementationReportUseCase(adapter, analytics_port=analytics_port)

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

    # Validate analytics section is included
    assert "Graph Analytics (Decisions)" in report.markdown
    assert "Critical Decisions (by indegree)" in report.markdown
    assert "`D1` — score 5.00" in report.markdown
    assert "`D2` — score 3.00" in report.markdown
    assert "Cycles" in report.markdown
    assert "Cycle 1: D1 -> D2 -> D1" in report.markdown
    assert "Topological Layers" in report.markdown
    assert "Layer 0: D1" in report.markdown
    assert "Layer 1: D2, D3" in report.markdown
    assert "Layer 2: D4" in report.markdown

    # Validate analytics port was called correctly
    analytics_port.get_critical_decisions.assert_called_once_with(case_id, limit=10)
    analytics_port.find_cycles.assert_called_once_with(case_id, max_depth=6)
    analytics_port.topo_layers.assert_called_once_with(case_id)


def test_report_usecase_e2e_analytics_empty_results():
    url = "redis://:swefleet-dev@localhost:6379/0"
    r: redis.Redis = redis.Redis.from_url(url, decode_responses=True)

    case_id = f"e2e-analytics-empty-{int(time.time())}"
    _cleanup_case(r, case_id)

    # Seed case spec
    spec_doc: dict[str, Any] = {
        "case_id": case_id,
        "title": "E2E Analytics Empty Case",
        "description": "End-to-end report generation with empty analytics",
        "acceptance_criteria": ["works with empty analytics"],
        "constraints": {"env": "prod"},
        "requester_id": "user-1",
        "tags": ["e2e", "analytics"],
        "created_at_ms": int(time.time() * 1000),
    }
    r.set(_k_spec(case_id), json.dumps(spec_doc))

    # Seed plan draft
    draft_doc: dict[str, Any] = {
        "plan_id": "P1",
        "case_id": case_id,
        "version": 1,
        "status": "draft",
        "author_id": "bot",
        "rationale": "because empty analytics",
        "created_at_ms": int(time.time() * 1000),
        "subtasks": [],
    }
    r.set(_k_draft(case_id), json.dumps(draft_doc))

    # Build use case with Redis-backed adapter and empty analytics port
    adapter = RedisPlanningReadAdapter(r)
    analytics_port = MagicMock()
    analytics_port.get_critical_decisions.return_value = []
    analytics_port.find_cycles.return_value = []
    analytics_port.topo_layers.return_value = LayeredTopology(layers=[])
    
    usecase = ImplementationReportUseCase(adapter, analytics_port=analytics_port)

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

    # Validate analytics section shows empty states
    assert "Graph Analytics (Decisions)" in report.markdown
    assert "Critical Decisions (by indegree)" in report.markdown
    assert "- (none)" in report.markdown
    assert "Cycles" in report.markdown
    assert "- (none)" in report.markdown
    assert "Topological Layers" in report.markdown
    assert "- (none)" in report.markdown

    # Validate analytics port was called correctly
    analytics_port.get_critical_decisions.assert_called_once_with(case_id, limit=10)
    analytics_port.find_cycles.assert_called_once_with(case_id, max_depth=6)
    analytics_port.topo_layers.assert_called_once_with(case_id)
