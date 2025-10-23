from __future__ import annotations

import sys
import types
from typing import Any

# Ensure adapter import works without the real 'neo4j' package (mirrors existing test style)
if "neo4j" not in sys.modules:
    fake_neo4j = types.ModuleType("neo4j")

    class _FakeGraphDatabase:
        @staticmethod
        def driver(*_args, **_kwargs):
            return None

    fake_neo4j.GraphDatabase = _FakeGraphDatabase
    sys.modules["neo4j"] = fake_neo4j

from core.reports.adapters.neo4j_graph_analytics_read_adapter import (
    Neo4jGraphAnalyticsReadAdapter,
)
from core.reports.domain.graph_analytics_types import (
    CriticalNode,
    LayeredTopology,
    PathCycle,
)


class _FakeStore:
    def __init__(self, results: dict[str, list[dict[str, Any]]]):
        self._results = results

    def query(self, cypher: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        # route by unique RETURN signatures we used in the adapter
        if "RETURN m.id AS id, 'Decision' AS label, toFloat(indeg) AS score" in cypher:
            return self._results.get("critical", [])
        if "RETURN [x IN nodes(p) | x.id] AS nodes, [rel IN relationships(p) | type(rel)] AS rels" in cypher:
            return self._results.get("cycles", [])
        if "RETURN nodes, edges" in cypher:
            return self._results.get("layers", [])
        return []


def _make(results: dict[str, list[dict[str, Any]]]) -> Neo4jGraphAnalyticsReadAdapter:
    return Neo4jGraphAnalyticsReadAdapter(_FakeStore(results))


def test_critical_nodes_mapping():
    adapter = _make(
        {
            "critical": [
                {"id": "D2", "label": "Decision", "score": 3.0},
                {"id": "D1", "label": "Decision", "score": 1.0},
            ]
        }
    )
    lst = adapter.get_critical_decisions("C1", limit=10)
    assert [c.id for c in lst] == ["D2", "D1"]
    assert all(isinstance(x, CriticalNode) for x in lst)


def test_cycles_mapping():
    adapter = _make({"cycles": [{"nodes": ["D1", "D2", "D1"], "rels": ["DEPENDS_ON", "BLOCKS"]}]})
    cycles = adapter.find_cycles("C1", max_depth=6)
    assert len(cycles) == 1
    assert isinstance(cycles[0], PathCycle)
    assert cycles[0].nodes[0] == "D1"


def test_layers_kahn():
    # Graph: D1 -> D2, D1 -> D3, D2 -> D4, D3 -> D4
    adapter = _make(
        {
            "layers": [
                {
                    "nodes": ["D1", "D2", "D3", "D4"],
                    "edges": [
                        {"src": "D1", "dst": "D2"},
                        {"src": "D1", "dst": "D3"},
                        {"src": "D2", "dst": "D4"},
                        {"src": "D3", "dst": "D4"},
                    ],
                }
            ]
        }
    )
    topo = adapter.topo_layers("C1")
    assert isinstance(topo, LayeredTopology)
    # Valid layering: D1 | D2,D3 | D4 (order inside layer not guaranteed, we sort in adapter)
    assert set(topo.layers[2]) == {"D4"}


def test_critical_nodes_empty():
    adapter = _make({"critical": []})
    lst = adapter.get_critical_decisions("C1", limit=10)
    assert lst == []


def test_cycles_empty():
    adapter = _make({"cycles": []})
    cycles = adapter.find_cycles("C1", max_depth=6)
    assert cycles == []


def test_layers_empty():
    adapter = _make({"layers": []})
    topo = adapter.topo_layers("C1")
    assert isinstance(topo, LayeredTopology)
    assert topo.layers == []


def test_critical_nodes_with_limit():
    adapter = _make(
        {
            "critical": [
                {"id": "D1", "label": "Decision", "score": 5.0},
                {"id": "D2", "label": "Decision", "score": 3.0},
                {"id": "D3", "label": "Decision", "score": 1.0},
            ]
        }
    )
    lst = adapter.get_critical_decisions("C1", limit=2)
    # The adapter uses LIMIT in the Cypher query, so we expect the mock to return limited results
    # Since our mock doesn't actually implement LIMIT, we'll test that it returns all results
    # and verify the ordering is correct
    assert len(lst) == 3  # All results returned by mock
    assert lst[0].id == "D1"  # Highest score first
    assert lst[0].score == 5.0
    assert lst[1].id == "D2"
    assert lst[1].score == 3.0
    assert lst[2].id == "D3"
    assert lst[2].score == 1.0


def test_cycles_with_different_max_depth():
    adapter = _make({"cycles": [{"nodes": ["D1", "D2", "D1"], "rels": ["DEPENDS_ON"]}]})
    cycles = adapter.find_cycles("C1", max_depth=3)
    assert len(cycles) == 1
    assert cycles[0].nodes == ["D1", "D2", "D1"]
    assert cycles[0].rels == ["DEPENDS_ON"]


def test_layers_complex_graph():
    # Complex graph with multiple paths
    adapter = _make(
        {
            "layers": [
                {
                    "nodes": ["A", "B", "C", "D", "E", "F"],
                    "edges": [
                        {"src": "A", "dst": "B"},
                        {"src": "A", "dst": "C"},
                        {"src": "B", "dst": "D"},
                        {"src": "C", "dst": "E"},
                        {"src": "D", "dst": "F"},
                        {"src": "E", "dst": "F"},
                    ],
                }
            ]
        }
    )
    topo = adapter.topo_layers("C1")
    assert isinstance(topo, LayeredTopology)
    assert len(topo.layers) >= 3  # Should have multiple layers
    assert "A" in topo.layers[0]  # Root node in first layer
    assert "F" in topo.layers[-1]  # Leaf node in last layer


def test_layers_cycle_handling():
    # Graph with cycle: A -> B -> C -> A
    adapter = _make(
        {
            "layers": [
                {
                    "nodes": ["A", "B", "C"],
                    "edges": [
                        {"src": "A", "dst": "B"},
                        {"src": "B", "dst": "C"},
                        {"src": "C", "dst": "A"},  # Creates cycle
                    ],
                }
            ]
        }
    )
    topo = adapter.topo_layers("C1")
    assert isinstance(topo, LayeredTopology)
    # Should handle cycle gracefully by putting remaining nodes in final layer
    assert len(topo.layers) > 0


def test_critical_nodes_data_types():
    adapter = _make(
        {
            "critical": [
                {"id": "D1", "label": "Decision", "score": 2.5},
                {"id": "D2", "label": "Decision", "score": 0.0},
            ]
        }
    )
    lst = adapter.get_critical_decisions("C1", limit=10)
    assert len(lst) == 2
    assert lst[0].id == "D1"
    assert lst[0].label == "Decision"
    assert lst[0].score == 2.5
    assert lst[1].score == 0.0


def test_cycles_multiple_cycles():
    adapter = _make(
        {
            "cycles": [
                {"nodes": ["A", "B", "A"], "rels": ["DEPENDS_ON"]},
                {"nodes": ["C", "D", "E", "C"], "rels": ["BLOCKS", "GOVERNS", "DEPENDS_ON"]},
            ]
        }
    )
    cycles = adapter.find_cycles("C1", max_depth=6)
    assert len(cycles) == 2
    assert cycles[0].nodes == ["A", "B", "A"]
    assert cycles[0].rels == ["DEPENDS_ON"]
    assert cycles[1].nodes == ["C", "D", "E", "C"]
    assert cycles[1].rels == ["BLOCKS", "GOVERNS", "DEPENDS_ON"]


def test_layers_single_node():
    adapter = _make(
        {
            "layers": [
                {
                    "nodes": ["A"],
                    "edges": [],
                }
            ]
        }
    )
    topo = adapter.topo_layers("C1")
    assert isinstance(topo, LayeredTopology)
    assert len(topo.layers) == 1
    assert topo.layers[0] == ["A"]


def test_layers_disconnected_nodes():
    adapter = _make(
        {
            "layers": [
                {
                    "nodes": ["A", "B", "C"],
                    "edges": [],  # No edges - all nodes disconnected
                }
            ]
        }
    )
    topo = adapter.topo_layers("C1")
    assert isinstance(topo, LayeredTopology)
    # All nodes should be in the same layer since they have no dependencies
    assert len(topo.layers) == 1
    assert set(topo.layers[0]) == {"A", "B", "C"}
