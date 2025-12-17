"""Quick coverage for graph_analytics_types.py - 1 line"""

import pytest
from core.reports.domain.graph_analytics_types import AgentMetrics


def test_agent_metrics_to_dict():
    """Test AgentMetrics.to_dict() method (line 34)."""
    metrics = AgentMetrics(
        agent_id="agent-001",
        total_runs=100,
        success_rate=0.95,
        p50_duration_ms=500.0,
        p95_duration_ms=1200.0,
    )

    result = metrics.to_dict()

    assert result["agent_id"] == "agent-001"
    assert result["total_runs"] == 100
    assert result["success_rate"] == pytest.approx(0.95)
    assert result["p50_duration_ms"] == pytest.approx(500.0)
    assert result["p95_duration_ms"] == pytest.approx(1200.0)
