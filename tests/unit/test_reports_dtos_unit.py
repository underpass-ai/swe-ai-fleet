from dataclasses import FrozenInstanceError

import pytest

from core.reports.dtos.dtos import (
    CaseSpecDTO,
    PlanningEventDTO,
    PlanVersionDTO,
    SubtaskPlanDTO,
)


def test_casespecdto_defaults_and_frozen():
    dto = CaseSpecDTO(
        case_id="C1",
        title="Title",
        description="Desc",
    )
    assert dto.acceptance_criteria == []
    assert dto.constraints == {}
    assert dto.requester_id == ""
    assert dto.tags == []
    assert dto.created_at_ms == 0

    with pytest.raises(FrozenInstanceError):
        dto.title = "New"


def test_casespecdto_default_factory_independence():
    a = CaseSpecDTO(case_id="A", title="t", description="d")
    b = CaseSpecDTO(case_id="B", title="t", description="d")

    assert a.acceptance_criteria is not b.acceptance_criteria
    assert a.constraints is not b.constraints
    assert a.tags is not b.tags

    a.acceptance_criteria.append("x")
    a.constraints["k"] = "v"
    a.tags.append("t1")

    assert b.acceptance_criteria == []
    assert b.constraints == {}
    assert b.tags == []


def test_subtaskplandto_defaults_and_frozen():
    dto = SubtaskPlanDTO(
        subtask_id="S1",
        title="Sub",
        description="Do it",
        role="dev",
    )
    assert dto.suggested_tech == []
    assert dto.depends_on == []
    assert dto.estimate_points == 0.0
    assert dto.priority == 0
    assert dto.risk_score == 0.0
    assert dto.notes == ""

    with pytest.raises(FrozenInstanceError):
        dto.priority = 1


def test_subtaskplandto_default_factory_independence():
    a = SubtaskPlanDTO(subtask_id="S1", title="t", description="d", role="dev")
    b = SubtaskPlanDTO(subtask_id="S2", title="t", description="d", role="dev")

    assert a.suggested_tech is not b.suggested_tech
    assert a.depends_on is not b.depends_on

    a.suggested_tech.append("python")
    a.depends_on.append("S0")

    assert b.suggested_tech == []
    assert b.depends_on == []


def test_planversiondto_defaults_frozen_and_subtasks():
    pv = PlanVersionDTO(
        plan_id="P1",
        case_id="C1",
        version=1,
        status="draft",
        author_id="U1",
    )
    assert pv.rationale == ""
    assert pv.subtasks == []
    assert pv.created_at_ms == 0

    with pytest.raises(FrozenInstanceError):
        pv.status = "final"

    # Ensure can hold subtasks
    st = SubtaskPlanDTO(
        subtask_id="S1",
        title="t",
        description="d",
        role="dev",
    )
    pv2 = PlanVersionDTO(
        plan_id="P2",
        case_id="C1",
        version=2,
        status="draft",
        author_id="U1",
        subtasks=[st],
    )
    assert len(pv2.subtasks) == 1
    assert pv2.subtasks[0] is st


def test_planversiondto_default_subtasks_independent():
    a = PlanVersionDTO(
        plan_id="P1",
        case_id="C",
        version=1,
        status="s",
        author_id="u",
    )
    b = PlanVersionDTO(
        plan_id="P2",
        case_id="C",
        version=1,
        status="s",
        author_id="u",
    )

    assert a.subtasks is not b.subtasks

    a.subtasks.append(
        SubtaskPlanDTO(
            subtask_id="S1",
            title="t",
            description="d",
            role="dev",
        )
    )
    assert b.subtasks == []


def test_planningeventdto_basic_and_equality():
    e1 = PlanningEventDTO(
        id="E1",
        event="created",
        actor="user",
        payload={"k": "v"},
        ts_ms=123,
    )
    e2 = PlanningEventDTO(
        id="E1",
        event="created",
        actor="user",
        payload={"k": "v"},
        ts_ms=123,
    )
    assert e1 == e2

    with pytest.raises(FrozenInstanceError):
        e1.actor = "bot"


def test_hashing_raises_for_mutable_fields():
    # Frozen dataclasses include mutable fields (lists/dicts),
    # so hashing should fail.
    dto = CaseSpecDTO(case_id="C1", title="t", description="d")
    with pytest.raises(TypeError):
        hash(dto)
