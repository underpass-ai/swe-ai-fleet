from dataclasses import FrozenInstanceError

import pytest

from core.reports.domain.decision_edges import DecisionEdges
from core.reports.domain.decision_enriched_report import (
    DecisionEnrichedReport,
)
from core.reports.domain.decision_node import DecisionNode
from core.reports.domain.subtask_node import SubtaskNode


def test_decisionedges_basic_and_frozen():
    edge1 = DecisionEdges(src_id="N1", rel_type="DEPENDS_ON", dst_id="N2")
    edge2 = DecisionEdges(src_id="N1", rel_type="DEPENDS_ON", dst_id="N2")

    assert edge1 == edge2
    assert isinstance(hash(edge1), int)

    with pytest.raises(FrozenInstanceError):
        edge1.rel_type = "CAUSES"


def test_decisionnode_basic_and_frozen():
    node1 = DecisionNode(
        id="D1",
        title="Choose approach",
        rationale="Faster to implement",
        status="accepted",
        created_at_ms=123456,
        author_id="U1",
    )
    node2 = DecisionNode(
        id="D1",
        title="Choose approach",
        rationale="Faster to implement",
        status="accepted",
        created_at_ms=123456,
        author_id="U1",
    )

    assert node1 == node2
    assert isinstance(hash(node1), int)

    with pytest.raises(FrozenInstanceError):
        node1.title = "New title"


def test_subtasknode_basic_and_frozen():
    st1 = SubtaskNode(id="S1", title="Implement X", role="dev")
    st2 = SubtaskNode(id="S1", title="Implement X", role="dev")

    assert st1 == st2
    assert isinstance(hash(st1), int)

    with pytest.raises(FrozenInstanceError):
        st1.role = "qa"


def test_decisionenrichedreport_defaults_frozen_and_stats_independence():
    rpt1 = DecisionEnrichedReport(
        case_id="C1",
        plan_id=None,
        generated_at_ms=1,
        markdown="# Report\n",
    )
    rpt2 = DecisionEnrichedReport(
        case_id="C2",
        plan_id=None,
        generated_at_ms=2,
        markdown="# Report\n",
    )

    assert rpt1.stats == {}
    assert rpt2.stats == {}
    assert rpt1.stats is not rpt2.stats

    rpt1.stats["k"] = "v"
    assert rpt2.stats == {}

    with pytest.raises(FrozenInstanceError):
        rpt1.markdown = "updated"


def test_decisionenrichedreport_equality_and_hashing_raises():
    a = DecisionEnrichedReport(
        case_id="C1",
        plan_id="P1",
        generated_at_ms=123,
        markdown="m",
    )
    b = DecisionEnrichedReport(
        case_id="C1",
        plan_id="P1",
        generated_at_ms=123,
        markdown="m",
    )

    assert a == b

    with pytest.raises(TypeError):
        hash(a)
