"""Tests for DerivationPhase value object."""

from __future__ import annotations

import pytest

from task_derivation.domain.value_objects.task_derivation.context.derivation_phase import (
    DerivationPhase,
)


def test_from_value_returns_enum_member() -> None:
    assert DerivationPhase.from_value("plan") is DerivationPhase.PLAN


def test_from_value_defaults_to_plan_when_none() -> None:
    assert DerivationPhase.from_value(None) is DerivationPhase.PLAN


def test_from_value_rejects_invalid_value() -> None:
    with pytest.raises(ValueError, match="Invalid derivation phase"):
        DerivationPhase.from_value("invalid")

