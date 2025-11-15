"""Tests for plan-related content value objects."""

from __future__ import annotations

import pytest

from task_derivation.domain.value_objects.content import (
    AcceptanceCriteria,
    AcceptanceCriterion,
    PlanDescription,
    TechnicalNotes,
)


def test_plan_description_rejects_blank_value() -> None:
    with pytest.raises(ValueError):
        PlanDescription(" ")


def test_plan_description_accepts_valid_value() -> None:
    desc = PlanDescription("Valid plan")
    assert str(desc) == "Valid plan"


def test_plan_description_rejects_long_value() -> None:
    with pytest.raises(ValueError):
        PlanDescription("x" * 5001)


def test_technical_notes_rejects_blank_value() -> None:
    with pytest.raises(ValueError):
        TechnicalNotes("")


def test_technical_notes_accepts_value() -> None:
    notes = TechnicalNotes("Use FastAPI")
    assert str(notes) == "Use FastAPI"


def test_acceptance_criterion_rejects_blank_value() -> None:
    with pytest.raises(ValueError):
        AcceptanceCriterion("")


def test_acceptance_criteria_from_iterable() -> None:
    criteria = AcceptanceCriteria.from_iterable(["AC1", "AC2"])
    assert len(criteria) == 2
    assert [str(c) for c in criteria] == ["AC1", "AC2"]


def test_acceptance_criteria_rejects_empty_iterable() -> None:
    with pytest.raises(ValueError):
        AcceptanceCriteria.from_iterable([])

