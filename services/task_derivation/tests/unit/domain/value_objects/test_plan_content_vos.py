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


def test_acceptance_criteria_direct_instantiation_with_valid_tuple() -> None:
    """Test direct instantiation with valid tuple of AcceptanceCriterion objects."""
    criterion1 = AcceptanceCriterion("AC1")
    criterion2 = AcceptanceCriterion("AC2")
    criteria = AcceptanceCriteria((criterion1, criterion2))
    assert len(criteria) == 2
    assert list(criteria) == [criterion1, criterion2]


def test_acceptance_criteria_direct_instantiation_rejects_empty_tuple() -> None:
    """Test that direct instantiation with empty tuple raises ValueError."""
    with pytest.raises(ValueError, match="AcceptanceCriteria cannot be empty"):
        AcceptanceCriteria(())


def test_acceptance_criteria_iteration() -> None:
    """Test that AcceptanceCriteria is iterable."""
    criteria = AcceptanceCriteria.from_iterable(["AC1", "AC2", "AC3"])
    items = list(criteria)
    assert len(items) == 3
    assert all(isinstance(item, AcceptanceCriterion) for item in items)
    assert [str(item) for item in items] == ["AC1", "AC2", "AC3"]


def test_acceptance_criteria_length() -> None:
    """Test that len() works correctly on AcceptanceCriteria."""
    criteria = AcceptanceCriteria.from_iterable(["AC1"])
    assert len(criteria) == 1

    criteria = AcceptanceCriteria.from_iterable(["AC1", "AC2", "AC3", "AC4"])
    assert len(criteria) == 4


def test_acceptance_criteria_from_iterable_with_single_item() -> None:
    """Test from_iterable with a single item."""
    criteria = AcceptanceCriteria.from_iterable(["Single AC"])
    assert len(criteria) == 1
    assert str(list(criteria)[0]) == "Single AC"


def test_acceptance_criteria_immutability() -> None:
    """Test that AcceptanceCriteria is immutable (frozen dataclass)."""
    criterion = AcceptanceCriterion("AC1")
    criteria = AcceptanceCriteria((criterion,))

    with pytest.raises(Exception):  # FrozenInstanceError
        criteria.values = (AcceptanceCriterion("AC2"),)  # type: ignore

