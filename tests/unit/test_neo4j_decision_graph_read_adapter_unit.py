from __future__ import annotations

import sys
import types
from typing import Any

# Ensure adapter import works without the real 'neo4j' package
if "neo4j" not in sys.modules:
    fake_neo4j = types.ModuleType("neo4j")

    class _FakeGraphDatabase:
        @staticmethod
        def driver(*_args, **_kwargs):
            return None

    fake_neo4j.GraphDatabase = _FakeGraphDatabase
    sys.modules["neo4j"] = fake_neo4j

from swe_ai_fleet.reports.adapters.neo4j_decision_graph_read_adapter import (
    Neo4jDecisionGraphReadAdapter,
)
from swe_ai_fleet.reports.domain.decision_edges import DecisionEdges
from swe_ai_fleet.reports.domain.decision_node import DecisionNode
from swe_ai_fleet.reports.domain.subtask_node import SubtaskNode
from swe_ai_fleet.reports.dtos.dtos import PlanVersionDTO


class _FakeStore:
    def __init__(self, results_by_query: dict[str, list[dict[str, Any]]]):
        self._results_by_query = results_by_query

    def query(self, cypher: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        if "RETURN p.id AS plan_id" in cypher:
            return self._results_by_query.get("plan", [])
        if "RETURN d.id AS id" in cypher:
            return self._results_by_query.get("decisions", [])
        if "RETURN d1.id AS src" in cypher:
            return self._results_by_query.get("deps", [])
        if "RETURN d.id AS did" in cypher:
            return self._results_by_query.get("impacts", [])
        return []


def _make_adapter_with_fake(  # type: ignore[no-untyped-def]
    results_by_query: dict[str, list[dict[str, Any]]],
) -> Neo4jDecisionGraphReadAdapter:
    store = _FakeStore(results_by_query)
    return Neo4jDecisionGraphReadAdapter(store)


def test_get_plan_by_case_none():
    adapter = _make_adapter_with_fake({"plan": [], "decisions": [], "deps": [], "impacts": []})
    assert adapter.get_plan_by_case("C1") is None


def test_get_plan_by_case_maps_fields_and_defaults():
    adapter = _make_adapter_with_fake(
        {
            "plan": [
                {
                    "plan_id": "P1",
                    "case_id": None,
                    "version": "2",
                    "status": None,
                    "author_id": None,
                    "rationale": None,
                    "created_at_ms": "100",
                }
            ]
        },
    )

    pv = adapter.get_plan_by_case("C1")
    assert isinstance(pv, PlanVersionDTO)
    assert pv and pv.plan_id == "P1"
    assert pv.case_id == "C1"  # fallback to requested case_id
    assert pv.version == 2
    assert pv.status == "UNKNOWN"
    assert pv.author_id == "unknown"
    assert pv.rationale == ""
    assert pv.subtasks == []
    assert pv.created_at_ms == 100


def test_list_decisions_maps_records_and_defaults():
    adapter = _make_adapter_with_fake(
        {
            "decisions": [
                {
                    "id": "D1",
                    "title": "T1",
                    "rationale": "R",
                    "status": "accepted",
                    "created_at_ms": 10,
                    "author_id": "U1",
                },
                {
                    "id": "D2",
                    # title missing -> ""
                    "rationale": "",
                    # status missing -> PROPOSED
                    "created_at_ms": None,  # -> 0
                    # author_id missing -> unknown
                },
            ]
        },
    )

    out = adapter.list_decisions("C1")
    assert out == [
        DecisionNode(
            id="D1",
            title="T1",
            rationale="R",
            status="accepted",
            created_at_ms=10,
            author_id="U1",
        ),
        DecisionNode(
            id="D2",
            title="",
            rationale="",
            status="PROPOSED",
            created_at_ms=0,
            author_id="unknown",
        ),
    ]


def test_list_decision_dependencies_maps_edges():
    adapter = _make_adapter_with_fake({"deps": [{"src": "D1", "rel": "DEPENDS_ON", "dst": "D2"}]})
    out = adapter.list_decision_dependencies("C1")
    assert out == [DecisionEdges(src_id="D1", rel_type="DEPENDS_ON", dst_id="D2")]


def test_list_decision_impacts_maps_subtasks():
    adapter = _make_adapter_with_fake(
        {
            "impacts": [
                {"did": "D1", "sid": "S1", "stitle": "Sub1", "srole": "dev"},
                {"did": "D1", "sid": "S2", "stitle": None, "srole": None},
            ]
        },
    )

    out = adapter.list_decision_impacts("C1")
    assert out == [
        ("D1", SubtaskNode(id="S1", title="Sub1", role="dev")),
        ("D1", SubtaskNode(id="S2", title="", role="")),
    ]


def test_close_noop():
    adapter = _make_adapter_with_fake({})
    assert adapter.close() is None
